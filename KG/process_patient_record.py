#!/usr/bin/env python3
"""
Process patient record: Extract structured data from patient records using Gemini API.
"""

import argparse
import json
import sys
import os
from google import genai

# Load API key at module level
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
        if file_type == 'json':
            with open(path, 'r') as f:
                return json.load(f)
        else:
            encodings = ['utf-8', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read()
                        if content.strip():
                            return content
                except (UnicodeDecodeError, LookupError):
                    continue
            print(f"Error: Could not decode file {path}")
            sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {path}")
        sys.exit(1)


def save_file(path, content, file_type='text'):
    """Save content to a file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        if file_type == 'json':
            json.dump(content, f, indent=2)
        else:
            f.write(content)
    print(f"✓ Saved to {path}")


def extract_patient_record(record_text: str, data_dictionary: dict, prompt: str) -> dict:
    """Extract patient record data using Gemini API"""
    print("\nExtracting patient record data...")

    contents = f"""{prompt}

### Current Input:
Raw Patient Record:
{record_text}

Data Dictionary JSON:
{json.dumps(data_dictionary, indent=2)}

Please extract and return the patient record as a JSON object matching the data dictionary.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={
            "response_mime_type": "application/json",
        },
    )

    # Parse response text as JSON
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        print("Warning: Could not parse response as JSON")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Extract structured data from patient records")

    parser.add_argument("--patient_record_pdf", type=str, required=True, help="Path to patient record text file")
    parser.add_argument("--data_dictionary", type=str, required=True, help="Path to data dictionary JSON")
    parser.add_argument("--prompt", type=str, required=True, help="Path to extraction prompt")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory")
    parser.add_argument("--record-id", type=str, default=None, help="Record identifier")

    args = parser.parse_args()

    # Load inputs
    record_text = load_file(args.patient_record_pdf)
    data_dictionary = load_file(args.data_dictionary, file_type='json')
    prompt_text = load_file(args.prompt)

    # Generate record ID if not provided
    if not args.record_id:
        args.record_id = os.path.splitext(os.path.basename(args.patient_record_pdf))[0]

    # Extract patient record
    extracted_data = extract_patient_record(record_text, data_dictionary, prompt_text)

    # Save output
    save_file(f"{args.output_dir}/PatientRecord_{args.record_id}.json", extracted_data, file_type='json')
    # save_file(f"{args.output_dir}/PatientRecord_{args.record_id}.txt", record_text)

    print("\n✓ Patient record extraction completed!")


if __name__ == "__main__":
    main()
