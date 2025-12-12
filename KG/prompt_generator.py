"""
Prompt Generator Script
This script replaces placeholders in evaluation prompt templates with actual content from specified files.
"""

import os
import re
import argparse
import json


def extract_policy_id(file_path):
    """
    Extract policy ID from file path.
    Example: /path/to/Run_Time_Policy/LCD_39543/Policy_LCD_39543.txt -> LCD_39543
    """
    # Match pattern like LCD_39543 or NCD_230_4
    match = re.search(r'((?:LCD|NCD)_[\w]+)', file_path)
    if match:
        return match.group(1)
    return None


def get_prompt_type(prompt_path):
    """
    Determine the prompt type based on the prompt file name.
    Returns: 'data', 'patient', or 'condition'
    """
    prompt_name = os.path.basename(prompt_path)

    if 'data_dictionary_judge_prompt' in prompt_name:
        return 'data'
    elif 'patient_extraction_judge_prompt' in prompt_name:
        return 'patient'
    elif 'policy_condition_judge_prompt' in prompt_name:
        return 'condition'
    else:
        raise ValueError(f"Unknown prompt type for: {prompt_name}")


def read_file_content(file_path):
    """Read and return the content of a file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def replace_placeholders(prompt_content, replacements):
    """
    Replace placeholders in the prompt with actual content.

    Args:
        prompt_content: The original prompt text
        replacements: Dictionary with placeholder names as keys and file paths as values

    Returns:
        Updated prompt content with placeholders replaced
    """
    result = prompt_content

    # Define all possible placeholders
    placeholder_mapping = {
        'ORIGINAL_DOCUMENT_PLACEHOLDER': 'original_document',
        'ORIGINAL_PATIENT_PLACEHOLDER': 'original_patient',
        'EXTRACTED_DD_JSON_PLACEHOLDER': 'extracted_dd',
        'DATA_DICTIONARY_JSON_PLACEHOLDER': 'extracted_dd',
        'EXTRACTED_JSON_PLACEHOLDER': 'extracted_policy',
        'EXTRACTED_PAT_PLACEHOLDER': 'extracted_patient'
    }

    for placeholder, key in placeholder_mapping.items():
        if key in replacements and replacements[key]:
            file_path = replacements[key]
            content = read_file_content(file_path)
            result = result.replace(f'[{placeholder}]', content)

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Generate evaluation prompts by replacing placeholders with actual content.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # For data dictionary evaluation
  python prompt_generator.py \\
    --prompt KG/prompts/Evaluation/data_dictionary_judge_prompt.txt \\
    --original-document KG/Run_Time_Policy/LCD_39543/Policy_LCD_39543.txt \\
    --extracted-dd KG/Run_Time_Policy/LCD_39543/Data_dictionary_LCD_39543.json \\
    --output KG/Evaluation/

  # For patient extraction evaluation
  python prompt_generator.py \\
    --prompt KG/prompts/Evaluation/patient_extraction_judge_prompt.txt \\
    --original-document KG/Run_Time_Patient/Patient_84722025445_Policy_CGSURG_83/CGSURG_83_Record_001.txt \\
    --original-patient KG/Run_Time_Patient/Patient_84722025445_Policy_CGSURG_83/Patient_84722025445.json \\
    --extracted-patient KG/Run_Time_Patient/Patient_84722025445_Policy_CGSURG_83/Patient_data_8472-2025-445.json \\
    --output KG/Evaluation/

  # For policy condition evaluation
  python prompt_generator.py \\
    --prompt KG/prompts/Evaluation/policy_condition_judge_prompt.txt \\
    --original-document KG/Run_Time_Policy/LCD_39543/Policy_LCD_39543.txt \\
    --extracted-dd KG/Run_Time_Policy/LCD_39543/Data_dictionary_LCD_39543.json \\
    --extracted-policy KG/Run_Time_Policy/LCD_39543/Policy_LCD_39543.json \\
    --output KG/Evaluation/
        """
    )

    parser.add_argument(
        '--prompt',
        required=True,
        help='Path to the prompt template file'
    )

    parser.add_argument(
        '--original-document',
        help='Path to the original document (for ORIGINAL_DOCUMENT_PLACEHOLDER)'
    )

    parser.add_argument(
        '--original-patient',
        help='Path to the original patient document (for patient evaluation)'
    )

    parser.add_argument(
        '--extracted-dd',
        help='Path to the extracted data dictionary JSON'
    )

    parser.add_argument(
        '--extracted-policy',
        help='Path to the extracted policy conditions JSON'
    )

    parser.add_argument(
        '--extracted-patient',
        help='Path to the extracted patient data JSON'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output directory or file path. If directory, filename will be auto-generated.'
    )

    args = parser.parse_args()

    # Read the prompt template
    prompt_content = read_file_content(args.prompt)

    # Prepare replacements
    replacements = {
        'original_document': args.original_document,
        'original_patient': args.original_patient,
        'extracted_dd': args.extracted_dd,
        'extracted_policy': args.extracted_policy,
        'extracted_patient': args.extracted_patient
    }

    # Replace placeholders
    result_content = replace_placeholders(prompt_content, replacements)

    # Determine output file path
    if os.path.isdir(args.output) or args.output.endswith('/'):
        # Auto-generate filename
        prompt_type = get_prompt_type(args.prompt)

        # Try to extract policy ID from any of the provided file paths
        policy_id = None
        for key, file_path in replacements.items():
            if file_path:
                policy_id = extract_policy_id(file_path)
                if policy_id:
                    break

        if not policy_id:
            policy_id = 'unknown'

        filename = f"{policy_id}_{prompt_type}.txt"
        output_path = os.path.join(args.output, filename)
    else:
        output_path = args.output

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Write the result
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_content)

    print(f"✓ Generated prompt saved to: {output_path}")
    print(f"  - Prompt type: {get_prompt_type(args.prompt)}")
    print(f"  - Policy ID: {extract_policy_id(str(args.original_document or args.extracted_policy or args.extracted_patient or ''))}")


if __name__ == '__main__':
    main()
