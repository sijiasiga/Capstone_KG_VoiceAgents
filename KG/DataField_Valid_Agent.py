#!/usr/bin/env python3
"""
DataField Validation Agent using Gemini API.

Evaluates extracted data fields against a policy document and data dictionary
using a structured rubric-based approach.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import google.generativeai as genai


def load_file(file_path: str) -> str:
    """Load text content from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_json_file(file_path: str) -> dict | list:
    """Load JSON content from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_api_key(api_config_path: str) -> str:
    """Load Gemini API key from config file."""
    config = load_json_file(api_config_path)
    if isinstance(config, dict) and "gemini" in config:
        return config["gemini"]
    raise ValueError(f"No 'gemini' key found in {api_config_path}")


def create_evaluation_prompt(
    policy_text: str,
    extracted_json: dict | list,
    data_dictionary: list,
    evaluation_prompt_template: str,
) -> str:
    """Create the evaluation prompt for Gemini."""
    prompt = evaluation_prompt_template + "\n\n"
    prompt += f"POLICY_TEXT:\n{policy_text}\n\n"
    prompt += f"EXTRACTED_ENTITIES_JSON:\n{json.dumps(extracted_json, indent=2)}\n\n"
    prompt += f"DATA_DICTIONARY_JSON:\n{json.dumps(data_dictionary, indent=2)}\n\n"
    prompt += "Please evaluate the extracted entities according to the rubric."

    return prompt


def evaluate_with_gemini(
    policy_text: str,
    extracted_json: dict | list,
    data_dictionary: list,
    evaluation_prompt: str,
    api_key: str,
) -> dict:
    """
    Call Gemini API to evaluate the extracted data.

    Args:
        policy_text: The policy document text
        extracted_json: The extracted data fields
        data_dictionary: The expected data dictionary
        evaluation_prompt: The evaluation prompt/rubric
        api_key: Gemini API key

    Returns:
        Dictionary with evaluation results
    """
    genai.configure(api_key=api_key)

    # Create the evaluation prompt
    full_prompt = create_evaluation_prompt(
        policy_text, extracted_json, data_dictionary, evaluation_prompt
    )

    # Call Gemini API
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(full_prompt)

    # Extract JSON from response
    response_text = response.text

    # Try to parse JSON from response
    try:
        # Find JSON object in response
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
        else:
            result = {"raw_response": response_text}
    except json.JSONDecodeError:
        result = {"raw_response": response_text}

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DataField Validation Agent using Gemini API"
    )
    parser.add_argument(
        "--policy-text",
        required=True,
        help="Path to the policy text file",
    )
    parser.add_argument(
        "--data-dictionary",
        required=True,
        help="Path to the data dictionary JSON file (contains both expected schema and extracted values)",
    )
    parser.add_argument(
        "--evaluation-prompt",
        required=True,
        help="Path to the evaluation prompt file",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for evaluation results (optional, prints to stdout if not provided)",
    )

    args = parser.parse_args()

    # Load files
    print(f"Loading policy text from: {args.policy_text}")
    policy_text = load_file(args.policy_text)

    print(f"Loading data dictionary from: {args.data_dictionary}")
    data_dictionary = load_json_file(args.data_dictionary)

    print(f"Loading evaluation prompt from: {args.evaluation_prompt}")
    evaluation_prompt = load_file(args.evaluation_prompt)

    # Load API key from default location
    script_dir = Path(__file__).parent
    api_config_path = script_dir / "api.json"
    print(f"Loading API configuration from: {api_config_path}")
    api_key = load_api_key(str(api_config_path))

    # Evaluate with Gemini (data_dictionary serves as both schema and extracted data)
    print("\nCalling Gemini API for evaluation...")
    result = evaluate_with_gemini(
        policy_text, data_dictionary, data_dictionary, evaluation_prompt, api_key
    )

    # Add timestamp if not present
    if "timestamp_utc" not in result:
        result["timestamp_utc"] = datetime.utcnow().isoformat() + "Z"

    # Output results
    result_json = json.dumps(result, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result_json)
        print(f"\nEvaluation results saved to: {args.output}")
    else:
        print("\nEvaluation Results:")
        print(result_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
