"""
Database service for LEGO data
Replaces Rebrickable API calls with local SQLite database queries
"""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class LegoDatabaseService:
    def __init__(self, db_path: str = None):
        """Initialize the database service"""
        if db_path is None:
            db_path = Path('instance') / 'lego_data.db'
        
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found at {db_path}. Please run build_database.py first.")
    
    def get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def get_set_info(self, set_number: str) -> Optional[Dict]:
        """Get basic set information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get set info with theme name
            query = """
                SELECT s.set_num, s.name, s.year, s.theme_id, s.num_parts, s.img_url,
                       t.name as theme_name
                FROM sets s
                LEFT JOIN themes t ON s.theme_id = t.id
                WHERE s.set_num = ?
            """
            
            cursor.execute(query, (set_number,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'set_number': row['set_num'],
                'set_name': row['name'],
                'year': row['year'],
                'theme_id': row['theme_id'],
                'theme_name': row['theme_name'],
                'num_parts': row['num_parts'],
                'set_image': row['img_url'],
                'set_url': f"https://rebrickable.com/sets/{set_number}/"
            }
    
    def get_set_inventory(self, set_number: str) -> List[Dict]:
        """Get combined inventory parts for a set (including minifig parts)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get set parts
            set_parts_query = """
                SELECT 
                    ip.part_num,
                    p.name as part_name,
                    ip.color_id,
                    c.name as color_name,
                    c.rgb as color_rgb,
                    ip.quantity,
                    ip.is_spare,
                    ip.img_url as part_image_url,
                    pc.name as part_category,
                    'set' as source_type
                FROM inventory_parts ip
                JOIN inventories inv ON ip.inventory_id = inv.id
                JOIN parts p ON ip.part_num = p.part_num
                JOIN colors c ON ip.color_id = c.id
                LEFT JOIN part_categories pc ON p.part_cat_id = pc.id
                WHERE inv.set_num = ?
            """
            
            # Get minifig parts from minifigs included in this set
            minifig_parts_query = """
                SELECT 
                    ip.part_num,
                    p.name as part_name,
                    ip.color_id,
                    c.name as color_name,
                    c.rgb as color_rgb,
                    (ip.quantity * im.quantity) as quantity,
                    ip.is_spare,
                    ip.img_url as part_image_url,
                    pc.name as part_category,
                    'minifig' as source_type,
                    m.name as minifig_name,
                    m.fig_num as minifig_num
                FROM inventory_minifigs im
                JOIN inventories inv ON im.inventory_id = inv.id
                JOIN inventories minifig_inv ON minifig_inv.set_num = im.fig_num
                JOIN inventory_parts ip ON minifig_inv.id = ip.inventory_id
                JOIN parts p ON ip.part_num = p.part_num
                JOIN colors c ON ip.color_id = c.id
                LEFT JOIN part_categories pc ON p.part_cat_id = pc.id
                LEFT JOIN minifigs m ON im.fig_num = m.fig_num
                WHERE inv.set_num = ?
            """
            
            # Execute both queries
            cursor.execute(set_parts_query, (set_number,))
            set_parts = cursor.fetchall()
            
            cursor.execute(minifig_parts_query, (set_number,))
            minifig_parts = cursor.fetchall()
            
            # Combine and process all parts
            all_parts = set_parts + minifig_parts
            
            # Group parts by part_num + color_id + is_spare + is_minifig_part to keep categories separate
            part_groups = {}
            for row in all_parts:
                # Create a unique key that includes spare and minifig status
                is_minifig = row['source_type'] == 'minifig'
                key = (row['part_num'], row['color_id'], bool(row['is_spare']), is_minifig)
                
                if key in part_groups:
                    # Add to existing part
                    part_groups[key]['quantity'] += row['quantity']
                    # Add source info
                    if row['source_type'] == 'minifig':
                        if 'minifig_sources' not in part_groups[key]:
                            part_groups[key]['minifig_sources'] = []
                        part_groups[key]['minifig_sources'].append({
                            'minifig_name': row['minifig_name'],
                            'minifig_num': row['minifig_num'],
                            'quantity': row['quantity']
                        })
                else:
                    # Create new part entry
                    part_groups[key] = {
                        'part_number': row['part_num'],
                        'part_name': row['part_name'],
                        'color_id': row['color_id'],
                        'color_name': row['color_name'],
                        'color_rgb': row['color_rgb'],
                        'quantity': row['quantity'],
                        'is_spare': bool(row['is_spare']),
                        'is_minifig_part': is_minifig,
                        'part_image_url': row['part_image_url'],
                        'part_category': row['part_category'],
                        'source_type': row['source_type']
                    }
                    
                    # Add minifig source info if applicable
                    if row['source_type'] == 'minifig':
                        part_groups[key]['minifig_sources'] = [{
                            'minifig_name': row['minifig_name'],
                            'minifig_num': row['minifig_num'],
                            'quantity': row['quantity']
                        }]
            
            # Convert to list and get part images
            inventory = []
            for part_data in part_groups.values():
                # Get part image URL from elements table if not available
                part_image_url = part_data['part_image_url']
                if not part_image_url:
                    part_image_url = self.get_part_image_url(part_data['part_number'], part_data['color_id'])
                
                part_data['part_image_url'] = part_image_url
                inventory.append(part_data)
            
            # Sort by spare status, then by color (prioritizing color ID 9999), then by part category, then by part name
            inventory.sort(key=lambda x: (x['is_spare'], x['color_id'] != 9999, x['color_name'], x['part_category'] or '', x['part_name']))
            return inventory
    
    def get_part_image_url(self, part_num: str, color_id: int) -> str:
        """Get part image URL from elements table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Try to find element with image
            query = """
                SELECT element_id
                FROM elements
                WHERE part_num = ? AND color_id = ?
                LIMIT 1
            """
            
            cursor.execute(query, (part_num, color_id))
            row = cursor.fetchone()
            
            if row:
                element_id = row['element_id']
                return f"https://cdn.rebrickable.com/media/parts/photos/{element_id}.jpg"
            else:
                # Fallback to generic part image
                return f"https://cdn.rebrickable.com/media/parts/ldraw/{part_num}.png"
    
    def search_sets(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for sets by name or set number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            search_query = """
                SELECT s.set_num, s.name, s.year, s.theme_id, s.num_parts, s.img_url,
                       t.name as theme_name
                FROM sets s
                LEFT JOIN themes t ON s.theme_id = t.id
                WHERE s.set_num LIKE ? OR s.name LIKE ?
                ORDER BY s.year DESC, s.name
                LIMIT ?
            """
            
            search_term = f"%{query}%"
            cursor.execute(search_query, (search_term, search_term, limit))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'set_number': row['set_num'],
                    'set_name': row['name'],
                    'year': row['year'],
                    'theme_name': row['theme_name'],
                    'num_parts': row['num_parts'],
                    'set_image': row['img_url']
                })
            
            return results
    
    def get_set_suggestions(self, partial_set_number: str, limit: int = 10) -> List[Dict]:
        """Get set number suggestions with names based on partial input"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT set_num, name
                FROM sets
                WHERE set_num LIKE ?
                ORDER BY set_num
                LIMIT ?
            """
            
            search_term = f"{partial_set_number}%"
            cursor.execute(query, (search_term, limit))
            rows = cursor.fetchall()
            
            return [{'set_number': row['set_num'], 'set_name': row['name']} for row in rows]
    
    def get_theme_info(self, theme_id: int) -> Optional[Dict]:
        """Get theme information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, name, parent_id
                FROM themes
                WHERE id = ?
            """
            
            cursor.execute(query, (theme_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row['id'],
                'name': row['name'],
                'parent_id': row['parent_id']
            }
    
    def get_part_info(self, part_num: str) -> Optional[Dict]:
        """Get part information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT p.part_num, p.name, p.part_cat_id, p.part_material,
                       pc.name as part_category
                FROM parts p
                LEFT JOIN part_categories pc ON p.part_cat_id = pc.id
                WHERE p.part_num = ?
            """
            
            cursor.execute(query, (part_num,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'part_num': row['part_num'],
                'name': row['name'],
                'part_cat_id': row['part_cat_id'],
                'part_material': row['part_material'],
                'part_category': row['part_category']
            }
    
    def get_color_info(self, color_id: int) -> Optional[Dict]:
        """Get color information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, name, rgb, is_trans
                FROM colors
                WHERE id = ?
            """
            
            cursor.execute(query, (color_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row['id'],
                'name': row['name'],
                'rgb': row['rgb'],
                'is_trans': bool(row['is_trans'])
            }
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            tables = ['sets', 'themes', 'parts', 'colors', 'inventories', 'inventory_parts', 
                     'elements', 'minifigs', 'part_categories']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            return stats

# Global instance
db_service = LegoDatabaseService()
