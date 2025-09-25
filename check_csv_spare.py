#!/usr/bin/env python3
"""
Check spare parts in the CSV data for set 75001-1
"""

import csv
import sqlite3

def check_csv_spare_parts():
    # First, find the inventory_id for set 75001-1
    conn = sqlite3.connect('instance/lego_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM inventories WHERE set_num = '75001-1'")
    inventory_ids = cursor.fetchall()
    conn.close()
    
    print(f"Inventory IDs for set 75001-1: {[id[0] for id in inventory_ids]}")
    
    # Check CSV data
    spare_parts = []
    with open('instance/inventory_parts.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['inventory_id'] in [str(id[0]) for id in inventory_ids] and row['is_spare'] == 'True':
                spare_parts.append(row)
    
    print(f'\nSpare parts in CSV for set 75001-1: {len(spare_parts)}')
    for part in spare_parts:
        print(f'  {part["part_num"]} (color {part["color_id"]}) - Qty: {part["quantity"]}, Spare: {part["is_spare"]}')
    
    # Also check all parts for this set in CSV
    all_parts = []
    with open('instance/inventory_parts.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['inventory_id'] in [str(id[0]) for id in inventory_ids]:
                all_parts.append(row)
    
    print(f'\nAll parts in CSV for set 75001-1: {len(all_parts)} total')
    spare_count = 0
    for part in all_parts:
        if part['is_spare'] == 'True':
            spare_count += 1
            print(f'  SPARE: {part["part_num"]} (color {part["color_id"]}) - Qty: {part["quantity"]}')
        else:
            print(f'  Regular: {part["part_num"]} (color {part["color_id"]}) - Qty: {part["quantity"]}')
    
    print(f'\nSpare parts count in CSV: {spare_count}')

if __name__ == "__main__":
    check_csv_spare_parts()
