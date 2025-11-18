"""
Robust policy ID extractor from directory or file paths.

This module extracts policy IDs from directory names in the NCD_LCD_Syn_data structure.
It can accept either a directory path or a PDF file path.

The extraction rules are:
- For NCD policies: extract the code from directory (e.g., NCD230.4 -> NCD_230_4)
- For LCD policies: extract the code from directory (e.g., L34106 -> LCD_34106)
- For other policies without LCD/NCD pattern: preserve the directory name as-is (e.g., CGSURG_83 -> CGSURG_83)
- Preserve dots in the ID, convert to underscores for clean formatting
- If a PDF file path is provided, extract the policy ID from its parent directory

Examples:
    NCD_LCD_Syn_data/NCD230.4/ -> NCD_230_4
    NCD_LCD_Syn_data/L34106/ -> LCD_34106
    NCD_LCD_Syn_data/CGSURG_83/ -> CGSURG_83
    NCD_LCD_Syn_data/L34106/LCD - Percutaneous Vertebral Augmentation (L34106).pdf -> LCD_34106
"""

import re
import os
from pathlib import Path


def extract_policy_id_from_filename(filename: str) -> str:
    """
    Extract policy ID directly from a filename without needing the full path.
    This is useful for uploaded files where we only have the filename.

    Args:
        filename: Just the filename (e.g., "LCD - Spinal Cord (L34106).pdf" or "NCD230.4.pdf")

    Returns:
        Extracted policy ID string (e.g., "LCD_34106", "NCD_230_4")

    Raises:
        ValueError: If policy ID cannot be extracted from filename
    """
    # Try NCD pattern in filename with flexible spacing
    ncd_match = re.search(r'NCD[\s_\-]*(\d+(?:\.\d+)?)', filename, re.IGNORECASE)
    if ncd_match:
        code = ncd_match.group(1)
        code = code.replace('.', '_')
        return f"NCD_{code}"

    # Try LCD pattern in filename with flexible matching
    lcd_match = re.search(r'(?:LCD)?[\s_\-]*[Ll][\s_\-]*(\d+)', filename, re.IGNORECASE)
    if lcd_match:
        code = lcd_match.group(1)
        return f"LCD_{code}"

    # Try to extract from filename with parentheses pattern
    paren_match = re.search(r'\(([A-Za-z]?\d+(?:\.\d+)?)\)', filename)
    if paren_match:
        code = paren_match.group(1)
        if code and code[0].upper() == 'L':
            # LCD policy
            code = re.sub(r'[^\d]', '', code)  # Keep only digits
            return f"LCD_{code}"
        elif code and code[0].isdigit():
            # NCD policy (numeric code like 230.4)
            code = code.replace('.', '_')
            return f"NCD_{code}"

    # If no LCD/NCD pattern found, use stem as fallback
    from pathlib import Path
    stem = Path(filename).stem.replace(' ', '_')
    return stem


def extract_policy_id(file_dir: str) -> str:
    """
    Extract policy ID from a directory path or PDF file path.

    Args:
        file_dir: Path to the policy directory or PDF file (can be relative or absolute)
                  Should be a directory containing PDF files like:
                  - NCD_LCD_Syn_data/NCD230.4/
                  - NCD_LCD_Syn_data/L34106/
                  - NCD_LCD_Syn_data/CGSURG_83/
                  Or a PDF file path like:
                  - NCD_LCD_Syn_data/L34106/LCD - Percutaneous Vertebral Augmentation (L34106).pdf

    Returns:
        Extracted policy ID string (e.g., "NCD_230_4", "LCD_34106", "CGSURG_83")

    Raises:
        ValueError: If the path doesn't exist or policy ID cannot be extracted
    """

    # Normalize the path
    input_path = Path(file_dir).resolve()

    if not input_path.exists():
        raise ValueError(f"Path does not exist: {file_dir}")

    # If it's a file, try to extract from filename first
    if input_path.is_file():
        filename = input_path.name

        # Try NCD pattern in filename with more flexible spacing (check first)
        ncd_file_match = re.search(r'NCD[\s_\-]*(\d+(?:\.\d+)?)', filename, re.IGNORECASE)
        if ncd_file_match:
            code = ncd_file_match.group(1)
            code = code.replace('.', '_')
            return f"NCD_{code}"

        # Try LCD pattern in filename with more flexible matching
        lcd_file_match = re.search(r'(?:LCD)?[\s_\-]*[Ll][\s_\-]*(\d+)', filename, re.IGNORECASE)
        if lcd_file_match:
            code = lcd_file_match.group(1)
            return f"LCD_{code}"

        # Try to extract from filename with parentheses pattern (for codes like (230.4) or (L34106))
        paren_match = re.search(r'\(([A-Za-z]?\d+(?:\.\d+)?)\)', filename)
        if paren_match:
            code = paren_match.group(1)
            if code and code[0].upper() == 'L':
                # LCD policy
                code = re.sub(r'[^\d]', '', code)  # Keep only digits
                return f"LCD_{code}"
            elif code and code[0].isdigit():
                # NCD policy (numeric code like 230.4)
                code = code.replace('.', '_')
                return f"NCD_{code}"

        # If no match in filename, try the parent directory
        dir_path = input_path.parent
    elif input_path.is_dir():
        dir_path = input_path
    else:
        raise ValueError(f"Path is neither a file nor directory: {file_dir}")

    # Get the directory name (last component of the path)
    dir_name = dir_path.name

    # Rule 1: Try to extract NCD pattern (e.g., NCD230.4, NCD 230.4)
    ncd_match = re.match(r'^NCD[\s_]?(\d+\.?\d*)$', dir_name, re.IGNORECASE)
    if ncd_match:
        code = ncd_match.group(1)
        # Replace dots with underscores
        code = code.replace('.', '_')
        return f"NCD_{code}"

    # Rule 2: Try to extract LCD pattern (e.g., L34106, LCD34106)
    lcd_match = re.match(r'^(?:LCD)?[Ll]?(\d+)$', dir_name, re.IGNORECASE)
    if lcd_match:
        code = lcd_match.group(1)
        return f"LCD_{code}"

    # Rule 3: If no match, try to extract code from PDF filenames in the directory
    pdf_files = list(dir_path.glob('*.pdf'))

    if pdf_files:
        # Try to find policy ID in PDF filenames
        for pdf_file in pdf_files:
            filename = pdf_file.name

            # Try to extract from filename with parentheses pattern
            paren_match = re.search(r'\(([A-Za-z]\d+(?:\.\d+)?)\)', filename)
            if paren_match:
                code = paren_match.group(1)
                if code[0].upper() == 'L':
                    # LCD policy
                    code = re.sub(r'[^\d]', '', code)  # Keep only digits
                    return f"LCD_{code}"
                else:
                    # NCD policy
                    code = code.replace('.', '_')
                    return f"NCD_{code}"

            # Try NCD pattern in filename with more flexible spacing
            ncd_file_match = re.search(r'NCD[\s_\-]*(\d+(?:\.\d+)?)', filename, re.IGNORECASE)
            if ncd_file_match:
                code = ncd_file_match.group(1)
                code = code.replace('.', '_')
                return f"NCD_{code}"

            # Try LCD pattern in filename with more flexible matching
            lcd_file_match = re.search(r'(?:LCD)?[\s_\-]*[Ll][\s_\-]*(\d+)', filename, re.IGNORECASE)
            if lcd_file_match:
                code = lcd_file_match.group(1)
                return f"LCD_{code}"

    # Rule 4: If no LCD/NCD pattern found, return the directory name as-is (e.g., CGSURG_83)
    return dir_name


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract policy ID from directory path in NCD_LCD_Syn_data structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_policy_id.py --file_dir NCD_LCD_Syn_data/L34106
  python extract_policy_id.py --file_dir NCD_LCD_Syn_data/NCD230.4
  python extract_policy_id.py --file_dir /absolute/path/to/L34106
        """,
    )

    parser.add_argument(
        "--file_dir",
        required=True,
        help="Path to the policy directory",
    )

    args = parser.parse_args()

    try:
        policy_id = extract_policy_id(args.file_dir)
        print(policy_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
