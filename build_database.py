#!/usr/bin/env python3
"""
Script to build SQLite database from CSV files
Replaces Rebrickable API calls with local database queries
"""

import sqlite3
import csv
import os
from pathlib import Path

def create_database_schema(cursor):
    """Create all necessary tables in the database"""
    
    # Sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sets (
            set_num TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            year INTEGER,
            theme_id INTEGER,
            num_parts INTEGER,
            img_url TEXT
        )
    ''')
    
    # Themes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id INTEGER
        )
    ''')
    
    # Parts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            part_num TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            part_cat_id INTEGER,
            part_material TEXT
        )
    ''')
    
    # Part categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS part_categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    
    # Colors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS colors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rgb TEXT,
            is_trans BOOLEAN,
            num_parts INTEGER,
            num_sets INTEGER,
            y1 INTEGER,
            y2 INTEGER
        )
    ''')
    
    # Inventories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventories (
            id INTEGER PRIMARY KEY,
            version INTEGER,
            set_num TEXT,
            FOREIGN KEY (set_num) REFERENCES sets (set_num)
        )
    ''')
    
    # Inventory parts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_parts (
            inventory_id INTEGER,
            part_num TEXT,
            color_id INTEGER,
            quantity INTEGER,
            is_spare BOOLEAN,
            img_url TEXT,
            PRIMARY KEY (inventory_id, part_num, color_id),
            FOREIGN KEY (inventory_id) REFERENCES inventories (id),
            FOREIGN KEY (part_num) REFERENCES parts (part_num),
            FOREIGN KEY (color_id) REFERENCES colors (id)
        )
    ''')
    
    # Elements table (for part images)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elements (
            element_id TEXT PRIMARY KEY,
            part_num TEXT,
            color_id INTEGER,
            design_id TEXT,
            FOREIGN KEY (part_num) REFERENCES parts (part_num),
            FOREIGN KEY (color_id) REFERENCES colors (id)
        )
    ''')
    
    # Minifigs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS minifigs (
            fig_num TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            num_parts INTEGER,
            img_url TEXT
        )
    ''')
    
    # Inventory minifigs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_minifigs (
            inventory_id INTEGER,
            fig_num TEXT,
            quantity INTEGER,
            PRIMARY KEY (inventory_id, fig_num),
            FOREIGN KEY (inventory_id) REFERENCES inventories (id),
            FOREIGN KEY (fig_num) REFERENCES minifigs (fig_num)
        )
    ''')
    
    # Inventory sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_sets (
            inventory_id INTEGER,
            set_num TEXT,
            quantity INTEGER,
            PRIMARY KEY (inventory_id, set_num),
            FOREIGN KEY (inventory_id) REFERENCES inventories (id),
            FOREIGN KEY (set_num) REFERENCES sets (set_num)
        )
    ''')
    
    # Part relationships table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS part_relationships (
            rel_type TEXT,
            child_part_num TEXT,
            parent_part_num TEXT,
            PRIMARY KEY (rel_type, child_part_num, parent_part_num),
            FOREIGN KEY (child_part_num) REFERENCES parts (part_num),
            FOREIGN KEY (parent_part_num) REFERENCES parts (part_num)
        )
    ''')

def import_csv_data(cursor, csv_file, table_name, columns=None):
    """Import data from CSV file to SQLite table"""
    csv_path = Path('instance') / csv_file
    
    if not csv_path.exists():
        print(f"Warning: {csv_file} not found, skipping...")
        return
    
    print(f"Importing {csv_file}...")
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        # Get column names from CSV or use provided columns
        if columns:
            csv_columns = columns
        else:
            csv_columns = reader.fieldnames
        
        # Create placeholders for SQL insert
        placeholders = ', '.join(['?' for _ in csv_columns])
        columns_str = ', '.join(csv_columns)
        
        # Prepare insert statement
        insert_sql = f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        # Insert data
        batch_size = 1000
        batch = []
        
        for row in reader:
            # Convert values, handling empty strings and special cases
            values = []
            for col in csv_columns:
                value = row.get(col, '')
                
                # Handle empty strings and convert to None for NULL values
                if value == '':
                    value = None
                # Handle boolean values
                elif value in ['True', 'true', '1']:
                    value = 1
                elif value in ['False', 'false', '0']:
                    value = 0
                # Handle numeric values
                elif col in ['year', 'theme_id', 'num_parts', 'id', 'parent_id', 'part_cat_id', 
                           'version', 'inventory_id', 'color_id', 'quantity', 'y1', 'y2'] and value:
                    try:
                        value = int(value)
                    except ValueError:
                        value = None
                
                values.append(value)
            
            batch.append(values)
            
            if len(batch) >= batch_size:
                cursor.executemany(insert_sql, batch)
                batch = []
        
        # Insert remaining batch
        if batch:
            cursor.executemany(insert_sql, batch)
        
        print(f"  Imported {csv_path.name} successfully")

def create_indexes(cursor):
    """Create indexes for better query performance"""
    print("Creating indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_sets_theme_id ON sets(theme_id)",
        "CREATE INDEX IF NOT EXISTS idx_sets_year ON sets(year)",
        "CREATE INDEX IF NOT EXISTS idx_inventories_set_num ON inventories(set_num)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_parts_inventory_id ON inventory_parts(inventory_id)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_parts_part_num ON inventory_parts(part_num)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_parts_color_id ON inventory_parts(color_id)",
        "CREATE INDEX IF NOT EXISTS idx_parts_part_cat_id ON parts(part_cat_id)",
        "CREATE INDEX IF NOT EXISTS idx_colors_id ON colors(id)",
        "CREATE INDEX IF NOT EXISTS idx_themes_id ON themes(id)",
        "CREATE INDEX IF NOT EXISTS idx_elements_part_num ON elements(part_num)",
        "CREATE INDEX IF NOT EXISTS idx_elements_color_id ON elements(color_id)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    print("  Indexes created successfully")

def main():
    """Main function to build the database"""
    print("Building LEGO database from CSV files...")
    
    # Database file path
    db_path = Path('instance') / 'lego_data.db'
    
    # Remove existing database if it exists
    if db_path.exists():
        print(f"Removing existing database: {db_path}")
        db_path.unlink()
    
    # Create new database
    print(f"Creating new database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create schema
        print("Creating database schema...")
        create_database_schema(cursor)
        
        # Import CSV data
        print("Importing CSV data...")
        
        # Import in order to respect foreign key constraints
        import_csv_data(cursor, 'themes.csv', 'themes')
        import_csv_data(cursor, 'part_categories.csv', 'part_categories')
        import_csv_data(cursor, 'colors.csv', 'colors')
        import_csv_data(cursor, 'parts.csv', 'parts')
        import_csv_data(cursor, 'sets.csv', 'sets')
        import_csv_data(cursor, 'inventories.csv', 'inventories')
        import_csv_data(cursor, 'inventory_parts.csv', 'inventory_parts')
        import_csv_data(cursor, 'elements.csv', 'elements')
        import_csv_data(cursor, 'minifigs.csv', 'minifigs')
        import_csv_data(cursor, 'inventory_minifigs.csv', 'inventory_minifigs')
        import_csv_data(cursor, 'inventory_sets.csv', 'inventory_sets')
        import_csv_data(cursor, 'part_relationships.csv', 'part_relationships')
        
        # Create indexes
        create_indexes(cursor)
        
        # Commit changes
        conn.commit()
        
        # Print statistics
        print("\nDatabase statistics:")
        tables = ['sets', 'themes', 'parts', 'colors', 'inventories', 'inventory_parts', 
                 'elements', 'minifigs', 'part_categories', 'part_relationships']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count:,} records")
        
        print(f"\nDatabase created successfully: {db_path}")
        print(f"Database size: {db_path.stat().st_size / (1024*1024):.1f} MB")
        
    except Exception as e:
        print(f"Error creating database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
