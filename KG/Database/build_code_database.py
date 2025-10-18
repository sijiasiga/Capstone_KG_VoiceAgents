"""
Build code mapping database from CSV files.
Usage: python build_code_database.py
"""

import sqlite3
import csv
import os

def build_database():
    """Build the code mapping database from CSV files."""
    
    # File paths
    db_path = 'code_mapping.db'
    schema_path = 'code_mapping_schema.sql'
    
    csv_files = {
        'cpt_codes': 'cpt_codes.csv',
        'icd10_procedure_codes': 'icd10_procedure_codes.csv',
        'icd10_diagnosis_codes': 'icd10_diagnosis_codes.csv',
        'policy_code_mapping': 'policy_code_mapping.csv'
    }
    
    # Check if all CSV files exist
    for table_name, csv_file in csv_files.items():
        if not os.path.exists(csv_file):
            print(f"ERROR: {csv_file} not found!")
            return False
    
    # Check if schema exists
    if not os.path.exists(schema_path):
        print(f"ERROR: {schema_path} not found!")
        return False
    
    print(f"Creating database: {db_path}")
    
    # Create/connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load and execute schema
    print(f"Loading schema from: {schema_path}")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
        cursor.executescript(schema_sql)
    
    counts = {}

    # Helper function to load CSVs
    def load_csv(table_name, file_path, columns):
        print(f"\nLoading {table_name} from: {file_path}")
        with open(file_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            reader = csv.DictReader(f)
            # Strip whitespace from headers
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            print(f"   Fieldnames detected: {reader.fieldnames}")
            count = 0
            for row in reader:
                values = [row[col].strip() if row[col] else None for col in columns]
                placeholders = ', '.join(['?'] * len(columns))
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {table_name} ({', '.join(columns)})
                    VALUES ({placeholders})
                ''', values)
                count += 1
            counts[table_name] = count
            print(f"   Loaded {count} records")

    # Load all CSVs
    load_csv('cpt_codes', csv_files['cpt_codes'], ['code', 'description', 'category', 'status'])
    load_csv('icd10_procedure_codes', csv_files['icd10_procedure_codes'], ['code', 'description', 'category', 'status'])
    load_csv('icd10_diagnosis_codes', csv_files['icd10_diagnosis_codes'], ['code', 'description', 'category', 'status'])
    load_csv('policy_code_mapping', csv_files['policy_code_mapping'], ['policy_id', 'code_type', 'code', 'requirement_type'])
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS! Database created: {db_path}")
    print(f"{'='*60}")
    print(f"\nSummary:")
    for item, count in counts.items():
        print(f"   {item}: {count}")
    
    return True

if __name__ == "__main__":
    success = build_database()
    if not success:
        print("\n❌ Database creation failed!")
        exit(1)
