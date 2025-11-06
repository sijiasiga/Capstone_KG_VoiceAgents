#!/usr/bin/env python3
"""
Process policy: Extract data fields → Extract policy conditions → Convert to SQL
"""

import argparse
import json
import sys
import os
import re
from google import genai
from pydantic import BaseModel
from DataField import DataField as DataFieldClass
from Policy import Policy
from utils.extract_policy_id import extract_policy_id

# Pydantic models for structured API output
class DataFieldPydantic(BaseModel):
    name: str
    type: str
    description: str
    section: str

class Restriction(BaseModel):
    condition: str
    rule: str
    codes: list
    logic: str

class PolicyPydantic(BaseModel):
    name: str
    guideline_number: str
    description: str
    raw_text: str
    restrictions: list[Restriction]

# Load API key
with open('api.json', 'r') as f:
    config = json.load(f)

api_key = config.get('gemini')
if not api_key:
    print("Error: Gemini API key not found in api.json")
    sys.exit(1)

client = genai.Client(api_key=api_key)

def load_file(path, file_type='text'):
    """Load a file and return its content"""
    try:
        # Handle JSON files
        if file_type == 'json':
            with open(path, 'r') as f:
                return json.load(f)

        # Handle text files (including PDF converted to text)
        # Try UTF-8 first, then fall back to other encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()
                    if content.strip():  # Check if file has content
                        return content
            except (UnicodeDecodeError, LookupError):
                continue

        # If we get here, couldn't decode with any encoding
        print(f"Error: Could not decode file {path} with any encoding")
        sys.exit(1)

    except FileNotFoundError:
        print(f"Error: File not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {path}")
        sys.exit(1)

def save_file(path, content, file_type='text'):
    """Save content to a file"""
    try:
        with open(path, 'w') as f:
            if file_type == 'json':
                json.dump(content, f, indent=2)
            else:
                f.write(content)
        print(f"✓ Saved to {path}")
    except Exception as e:
        print(f"Error writing to {path}: {e}")
        sys.exit(1)

def extract_data_fields(policy_text, existing_dictionary, prompt_path):
    """Step 1: Extract data fields from policy"""
    print("\n[1/3] Extracting data fields...")

    prompt = load_file(prompt_path)

    contents = f"""{prompt}

### Current Input:
Raw Policy Text:
{policy_text}

Existing DataField JSON:
{json.dumps(existing_dictionary, indent=2)}

Please extract and return the updated DataField JSON.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[DataFieldPydantic],
        },
    )

    data_fields = response.parsed
    return [field.model_dump() for field in data_fields]

def extract_policy_conditions(policy_text, data_fields, prompt_path):
    """Step 2: Extract policy conditions"""
    print("[2/3] Extracting policy conditions...")

    prompt = load_file(prompt_path)

    contents = f"""{prompt}

### Current Input:
Data Dictionary JSON:
{json.dumps(data_fields, indent=2)}

Raw Policy Text:
{policy_text}

Please extract and return the Policy JSON.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[PolicyPydantic],
        },
    )

    policies = response.parsed
    return [policy.model_dump() for policy in policies]

def convert_to_sql(policy, prompt_path):
    """Step 3: Convert policy to SQL"""
    print("[3/3] Converting to SQL...")

    prompt = load_file(prompt_path)

    contents = f"""{prompt}

### Current Input:
Policy JSON:
{json.dumps(policy, indent=2)}

Please generate the SQL query.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
    )

    return response.text

def main():
    parser = argparse.ArgumentParser(
        description="Process medical policy: extract fields → extract conditions → convert to SQL"
    )

    parser.add_argument(
        "--policy",
        type=str,
        required=True,
        help="Path to policy text file (PDF or TXT)"
    )
    parser.add_argument(
        "--policy-id",
        type=str,
        default=None,
        help="Policy identifier for naming output files. If not provided, auto-extracted from filename"
    )
    parser.add_argument(
        "--dictionary",
        type=str,
        required=True,
        help="Path to initial data dictionary JSON"
    )
    parser.add_argument(
        "--datafield-prompt",
        type=str,
        required=True,
        help="Path to DataField extraction prompt"
    )
    parser.add_argument(
        "--policy-prompt",
        type=str,
        required=True,
        help="Path to Policy extraction prompt"
    )
    parser.add_argument(
        "--sql-prompt",
        type=str,
        required=True,
        help="Path to SQL conversion prompt"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save all output files"
    )

    args = parser.parse_args()

    # Auto-extract policy_id from filename if not provided
    if not args.policy_id:
        try:
            args.policy_id = extract_policy_id(args.policy)
            print(f"Auto-extracted policy_id: {args.policy_id}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print(f"Using provided policy_id: {args.policy_id}")

    # Load inputs
    policy_text = load_file(args.policy)
    existing_dictionary = load_file(args.dictionary, file_type='json')

    # Step 1: Extract data fields
    data_fields = extract_data_fields(
        policy_text,
        existing_dictionary,
        args.datafield_prompt
    )
    save_file(f"{args.output_dir}/Data_dictionary_{args.policy_id}.json", data_fields, file_type='json')

    # Step 2: Extract policy conditions
    policies = extract_policy_conditions(
        policy_text,
        data_fields,
        args.policy_prompt
    )
    save_file(f"{args.output_dir}/Policy_{args.policy_id}.json", policies, file_type='json')

    # Step 3: Convert to SQL (for each policy)
    sql_queries = []
    for policy in policies:
        sql = convert_to_sql(policy, args.sql_prompt)
        sql_queries.append(sql)

    save_file(f"{args.output_dir}/SQL_{args.policy_id}.txt", '\n\n---\n\n'.join(sql_queries))

    # Also save the OCR policy text
    save_file(f"{args.output_dir}/Policy_{args.policy_id}.txt", policy_text)

    print("\n✓ All steps completed!")

if __name__ == "__main__":
    main()
