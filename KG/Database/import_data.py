"""
Simple script to import patient data from JSON files into the database.
"""

import sqlite3
import json
import os
import argparse


def load_patient_data(filepath):
    """Load patient data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def import_patient_data(cursor, data_dir, table_name):
    """Import all patient data from JSON files in directory."""
    
    # Get all JSON files in directory
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    count = 0
    for filename in sorted(json_files):
        filepath = os.path.join(data_dir, filename)
        patient_data = load_patient_data(filepath)
        
        # Get field names and values directly (no mapping needed)
        field_names = list(patient_data.keys())
        values = list(patient_data.values())
        
        # Create INSERT statement
        placeholders = ','.join(['?' for _ in field_names])
        insert_sql = f"INSERT OR REPLACE INTO {table_name} ({','.join(field_names)}) VALUES ({placeholders})"
        
        try:
            cursor.execute(insert_sql, values)
            count += 1
            print(f"  ✓ Imported patient {patient_data.get('patient_id', 'unknown')}")
        except Exception as e:
            print(f"  ✗ Error importing {filename}: {e}")
    
    return count


def main():
    """Import patient data into database."""
    parser = argparse.ArgumentParser(description='Import patient data from JSON files')
    parser.add_argument('--database', '-d', default='policy_CGSURG83.db', help='Database file name')
    parser.add_argument('--data-dir', default='../test1/Patient_data_dictionary', help='Directory containing patient JSON files')
    parser.add_argument('--table', '-t', default='patient_bariatric_data', help='Table name')
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    
    # Handle relative paths
    if args.data_dir.startswith('../'):
        data_dir = os.path.join(project_root, args.data_dir[3:])
    else:
        data_dir = os.path.join(base_dir, args.data_dir)
    
    db_path = os.path.join(base_dir, args.database)
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        print(f"Data directory not found: {data_dir}")
        return
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Import data
    print(f"Importing data from: {data_dir}")
    count = import_patient_data(cursor, data_dir, args.table)
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\nImported {count} patient records into {args.table}")


if __name__ == "__main__":
    main()
