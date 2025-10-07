"""
Simple script to run SQL filter queries on the database.
"""

import sqlite3
import os
import argparse


def load_sql_file(filepath):
    """Load SQL query from file."""
    with open(filepath, 'r') as f:
        return f.read().strip()


def run_filter_query(cursor, sql_query):
    """Execute filter query and return results."""
    cursor.execute(sql_query)
    return cursor.fetchall()


def print_results(results, cursor):
    """Print query results in a formatted table."""
    if not results:
        print("No results found.")
        return
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    # Calculate column widths
    widths = [len(col) for col in columns]
    for row in results:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    
    # Print header
    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    print("\n" + header)
    print("-" * len(header))
    
    # Print rows
    for row in results:
        print(" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)))
    
    print(f"\n({len(results)} row{'s' if len(results) != 1 else ''} returned)")


def main():
    """Run SQL filter query on database."""
    parser = argparse.ArgumentParser(description='Run SQL filter queries on the database')
    parser.add_argument('--database', '-d', default='policy_CGSURG83.db', help='Database file name')
    parser.add_argument('--sql-file', '-s', default='../test1/Policy_CGSURG83/SQL_CGSURG83.txt', help='SQL file path')
    parser.add_argument('--output', '-o', choices=['table', 'csv', 'json'], default='table', help='Output format')
    parser.add_argument('--save', help='Save results to file (specify filename)')
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    
    # Handle relative paths
    if args.sql_file.startswith('../'):
        sql_path = os.path.join(project_root, args.sql_file[3:])
    else:
        sql_path = os.path.join(base_dir, args.sql_file)
    
    db_path = os.path.join(base_dir, args.database)
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    # Check if SQL file exists
    if not os.path.exists(sql_path):
        print(f"SQL file not found: {sql_path}")
        return
    
    # Load SQL query
    sql_query = load_sql_file(sql_path)
    print(f"Running query from: {sql_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute query
        results = run_filter_query(cursor, sql_query)
        
        # Prepare output content
        output_content = ""
        columns = [description[0] for description in cursor.description]
        
        if args.output == 'table':
            if not results:
                output_content = "No results found."
            else:
                # Calculate column widths
                widths = [len(col) for col in columns]
                for row in results:
                    for i, val in enumerate(row):
                        widths[i] = max(widths[i], len(str(val)))
                
                # Build table
                header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
                separator = "-" * len(header)
                rows = []
                for row in results:
                    rows.append(" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)))
                
                output_content = f"\n{header}\n{separator}\n" + "\n".join(rows) + f"\n\n({len(results)} row{'s' if len(results) != 1 else ''} returned)"
        
        elif args.output == 'csv':
            output_content = ",".join(columns) + "\n"
            for row in results:
                output_content += ",".join(str(val) if val is not None else '' for val in row) + "\n"
        
        elif args.output == 'json':
            import json
            json_data = [dict(zip(columns, row)) for row in results]
            output_content = json.dumps(json_data, indent=2)
        
        # Print and/or save results
        print(output_content)
        
        if args.save:
            with open(args.save, 'w') as f:
                f.write(output_content)
            print(f"\nResults saved to: {args.save}")
    
    except sqlite3.Error as e:
        print(f"SQL Error: {e}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
