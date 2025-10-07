"""
Script to create SQLite database from data dictionary JSON file.
"""

import sqlite3
import os
import argparse
import json


def load_data_dictionary(filepath: str):
    """Load data dictionary from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def create_table_from_dictionary(cursor: sqlite3.Cursor, data_dict: list, table_name: str = "patient_bariatric_data"):
    """Create table based on data dictionary."""
    
    # Map JSON types to SQLite types
    type_mapping = {
        'string': 'TEXT',
        'integer': 'INTEGER',
        'float': 'REAL',
        'boolean': 'INTEGER'
    }
    
    # Build column definitions
    columns = []
    for field in data_dict:
        field_name = field['name']
        field_type = type_mapping.get(field['type'], 'TEXT')
        columns.append(f"{field_name} {field_type}")
    
    # Create table
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
    cursor.execute(create_sql)


def main():
    """Create database from data dictionary."""
    parser = argparse.ArgumentParser(description='Create SQLite database from data dictionary JSON file')
    parser.add_argument('--database', '-d', default='policy_CGSURG83.db', help='Database file name')
    parser.add_argument('--dictionary', '-dict', default='../test1/Policy_CGSURG83/Data_dictionary_CGSURG83.json', help='Data dictionary JSON file')
    parser.add_argument('--table', '-t', default='patients', help='Table name')
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    
    # Handle relative paths
    if args.dictionary.startswith('../'):
        dict_path = os.path.join(project_root, args.dictionary[3:])
    else:
        dict_path = os.path.join(base_dir, args.dictionary)
    
    db_path = os.path.join(base_dir, args.database)
    
    # Check if data dictionary file exists
    if not os.path.exists(dict_path):
        print(f"Data dictionary file not found: {dict_path}")
        return
    
    # Load data dictionary
    data_dictionary = load_data_dictionary(dict_path)
    print(f"Loaded {len(data_dictionary)} fields from data dictionary")
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table from dictionary
    create_table_from_dictionary(cursor, data_dictionary, args.table)
    conn.commit()
    conn.close()
    
    print(f"Database created: {db_path}")
    print(f"Table '{args.table}' created with {len(data_dictionary)} columns")


if __name__ == "__main__":
    main()
