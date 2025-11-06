"""
Save policy information (ID) to a JSON file.

Examples:
    python save_policy_info.py --policy-id LCD_34106 --output-dir ./output
    # Creates: ./output/Info_LCD_34106.json with {"id": "LCD_34106"}
"""

import json
import sys
import argparse
from pathlib import Path


def save_policy_info(policy_id: str, output_dir: str) -> str:
    """
    Save policy ID to a JSON file.

    Args:
        policy_id: The policy ID string
        output_dir: Directory to save the JSON file

    Returns:
        Path to the created JSON file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    policy_info = {"id": policy_id}
    json_path = output_dir / f"Info_{policy_id}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(policy_info, f, indent=2, ensure_ascii=False)

    return str(json_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Save policy ID to a JSON file"
    )

    parser.add_argument(
        "--policy-id",
        required=True,
        help="The policy ID string",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save the JSON file",
    )

    args = parser.parse_args()

    try:
        json_path = save_policy_info(args.policy_id, args.output_dir)
        print(json_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
