#!/usr/bin/env python3
"""
Check spare parts in the database for set 75001-1
"""

import sqlite3

def check_spare_parts():
    conn = sqlite3.connect('instance/lego_data.db')
    cursor = conn.cursor()
    
    # Check spare parts in database
    cursor.execute("""
        SELECT ip.part_num, ip.color_id, ip.quantity, ip.is_spare 
        FROM inventory_parts ip 
        JOIN inventories inv ON ip.inventory_id = inv.id 
        WHERE inv.set_num = '75001-1' AND ip.is_spare = 1
    """)
    spare_parts = cursor.fetchall()
    
    print('Spare parts in database for 75001-1:')
    for part in spare_parts:
        print(f'  {part[0]} (color {part[1]}) - Qty: {part[2]}, Spare: {part[3]}')
    
    print(f'\nTotal spare parts found: {len(spare_parts)}')
    
    # Also check all parts for this set
    cursor.execute("""
        SELECT ip.part_num, ip.color_id, ip.quantity, ip.is_spare 
        FROM inventory_parts ip 
        JOIN inventories inv ON ip.inventory_id = inv.id 
        WHERE inv.set_num = '75001-1'
        ORDER BY ip.is_spare DESC, ip.part_num
    """)
    all_parts = cursor.fetchall()
    
    print(f'\nAll parts for set 75001-1: {len(all_parts)} total')
    spare_count = 0
    for part in all_parts:
        if part[3]:  # is_spare
            spare_count += 1
            print(f'  SPARE: {part[0]} (color {part[1]}) - Qty: {part[2]}')
        else:
            print(f'  Regular: {part[0]} (color {part[1]}) - Qty: {part[2]}')
    
    print(f'\nSpare parts count: {spare_count}')
    
    # Check for the missing parts specifically
    cursor.execute("""
        SELECT ip.part_num, ip.color_id, ip.quantity, ip.is_spare 
        FROM inventory_parts ip 
        JOIN inventories inv ON ip.inventory_id = inv.id 
        WHERE inv.set_num = '75001-1' AND ip.part_num IN ('6141', '98138')
    """)
    missing_parts = cursor.fetchall()
    
    print(f'\nMissing parts (6141, 98138) in database:')
    for part in missing_parts:
        print(f'  {part[0]} (color {part[1]}) - Qty: {part[2]}, Spare: {part[3]}')
    
    conn.close()

if __name__ == "__main__":
    check_spare_parts()
