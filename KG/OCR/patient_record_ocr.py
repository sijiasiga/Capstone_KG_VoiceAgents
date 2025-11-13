#!/usr/bin/env python3
"""
Enhanced OCR for patient record PDFs with two-layer text cleaning.

Layer 1: Improved OCR extraction with better parameters
Layer 2: Intelligent text post-processing to fix common issues

Usage: python patient_record_ocr.py <input_pdf_path> [--output <output_file>] [--no-clean]
"""

import argparse
import sys
import os
import io
import re
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import PyPDF2
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Error: Missing required library - {e}")
    print("Please install required packages:")
    print("pip install PyPDF2 pytesseract pillow PyMuPDF")
    sys.exit(1)


class PatientRecordOCRCleaner:
    """Intelligent text cleaner for patient record PDFs"""

    def __init__(self):
        """Initialize cleaner with patterns"""
        # Patterns to remove (metadata, disclaimers, etc.)
        self.remove_patterns = [
            # Timestamps
            r'\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?',
            # Page numbers (X/Y format, standalone or inline)
            r'\s*\d+/\d+\s*$',
            # URLs
            r'https?://[^\s]+',
            # Email addresses
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            # Social Security Number patterns (XXX-XX-XXXX)
            r'\d{3}-\d{2}-\d{4}',
            # Phone number patterns (multiple formats)
            r'[\(\s]?\d{3}[\)\s-]?\d{3}[-\s]?\d{4}',
        ]

        # Multi-line patterns (process separately with DOTALL flag)
        self.multiline_remove_patterns = [
            # Standard medical disclaimers and notices
            r'This is a confidential.*?(?:patient|record|information)\.',
            r'For office use only.*?end of document',
            # Copyright and legal notices (but preserve clinical content)
            r'(?:Copyright|©).*?(?:All Rights Reserved|All rights reserved)\.?',
            # Repeated headers across pages
            r'(?:Patient Name|Date of Birth|Patient ID).*?(?=\n\n)',
        ]

    def clean_text(self, text: str) -> str:
        """
        Apply two-layer cleaning to extracted text
        """
        # Layer 1: Remove metadata and disclaimers
        text = self._remove_metadata(text)

        # Layer 2: Fix structural issues
        text = self._fix_table_structure(text)
        text = self._deduplicate_headers(text)
        text = self._fix_line_breaks(text)
        text = self._normalize_whitespace(text)

        return text.strip()

    def _remove_metadata(self, text: str) -> str:
        """Remove metadata, URLs, timestamps, page numbers, and PII patterns"""
        # Apply single-line patterns
        for pattern in self.remove_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Apply multi-line patterns with DOTALL flag
        for pattern in self.multiline_remove_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

        return text

    def _deduplicate_headers(self, text: str) -> str:
        """
        Remove duplicate headers that appear multiple times across pages
        (e.g., "Patient Name", "Date of Birth", "Hospital", etc.)
        """
        lines = text.split('\n')
        seen_headers = set()
        filtered_lines = []

        common_headers = [
            'Patient Name', 'Date of Birth', 'Patient ID', 'MRN',
            'Hospital', 'Facility', 'Provider', 'Physician',
            'Diagnosis', 'Treatment', 'Medication', 'Allergies',
            'Lab Results', 'Vital Signs', 'Visit Date', 'Discharge Date'
        ]

        for line in lines:
            line_stripped = line.strip()

            # Check if this line looks like a header
            is_header = any(header in line_stripped for header in common_headers)

            if is_header:
                if line_stripped not in seen_headers:
                    filtered_lines.append(line)
                    seen_headers.add(line_stripped)
                # Skip duplicate headers
            else:
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _fix_table_structure(self, text: str) -> str:
        """
        Detect and fix broken table rows
        Example:
            Before: Patient Name / Date of Birth / Gender
                    John Doe / 01/15/1970 / M
            After:  Patient Name | Date of Birth | Gender
                    John Doe | 01/15/1970 | M

        This is a simplified approach - detects consecutive short lines that likely belong together
        """
        lines = text.split('\n')
        result = []
        buffer = []  # Buffer for potentially connected lines
        threshold = 80  # Lines shorter than this might be table cells

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped:
                if buffer:
                    # Flush buffer
                    result.append(' | '.join(buffer))
                    buffer = []
                result.append(line)
                continue

            # Check if line looks like a table cell (short and simple)
            is_likely_cell = (
                len(line_stripped) < threshold and
                not line_stripped.endswith('.') and
                not line_stripped.endswith(':') and
                re.match(r'^[A-Za-z0-9\-\s,\.()&:/]+$', line_stripped)
            )

            # Heuristic: if current + next line are both short, they likely belong together
            if is_likely_cell and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                next_is_cell = (
                    next_line and
                    len(next_line) < threshold and
                    not next_line.endswith('.') and
                    re.match(r'^[A-Za-z0-9\-\s,\.()&:/]+$', next_line)
                )

                if next_is_cell:
                    # Start buffering
                    buffer.append(line_stripped)
                    continue

            # If we reach here, check if we should flush buffer
            if buffer:
                buffer.append(line_stripped)
                result.append(' | '.join(buffer))
                buffer = []
            else:
                result.append(line)

        # Flush any remaining buffer
        if buffer:
            result.append(' | '.join(buffer))

        return '\n'.join(result)

    def _fix_line_breaks(self, text: str) -> str:
        """
        Fix artificial line breaks within sentences and clinical notes
        - Join lines that clearly continue from previous
        - Preserve paragraph breaks (multiple newlines)
        """
        # Split by paragraph (multiple newlines)
        paragraphs = re.split(r'\n\s*\n', text)
        fixed_paragraphs = []

        for para in paragraphs:
            lines = para.split('\n')
            fixed_lines = []
            i = 0

            while i < len(lines):
                line = lines[i].strip()

                # Check if next line should be joined with current
                if i < len(lines) - 1:
                    next_line = lines[i + 1].strip()

                    # Join if current line doesn't end with sentence-ending punctuation
                    # AND next line doesn't start with capital (likely new sentence/section)
                    should_join = (
                        line and
                        next_line and
                        not line.endswith(('.', ':', ';', ')', ']', '}')) and
                        not re.match(r'^[A-Z][a-z]+\s+[A-Z]', next_line)  # Avoid joining at section headers
                    )

                    if should_join:
                        fixed_lines.append(line + ' ' + next_line)
                        i += 2
                        continue

                if line:
                    fixed_lines.append(line)
                i += 1

            fixed_paragraphs.append('\n'.join(fixed_lines))

        return '\n\n'.join(fixed_paragraphs)

    def _normalize_whitespace(self, text: str) -> str:
        """
        - Convert multiple spaces to single space
        - Preserve paragraph structure
        - Clean up tabs
        """
        # Replace tabs with spaces
        text = text.replace('\t', ' ')

        # Split by paragraphs to preserve structure
        paragraphs = re.split(r'\n\s*\n', text)
        cleaned = []

        for para in paragraphs:
            # Normalize spaces within paragraph
            para = re.sub(r' +', ' ', para)  # Multiple spaces -> single space
            para = re.sub(r'\n +', '\n', para)  # Leading spaces on new lines
            para = re.sub(r' +\n', '\n', para)  # Trailing spaces before newlines
            cleaned.append(para.strip())

        return '\n\n'.join([p for p in cleaned if p])  # Remove empty paragraphs


def extract_text_from_pdf(pdf_path: str, cleaner: PatientRecordOCRCleaner = None) -> Dict:
    """
    Extract text from PDF with improved OCR parameters
    """
    text_data = {
        'file_path': str(pdf_path),
        'pages': [],
        'full_text': '',
        'metadata': {},
        'extraction_method': 'unknown'
    }

    try:
        # Method 1: PyMuPDF with optimized text extraction
        doc = fitz.open(pdf_path)
        text_data['metadata'] = {
            'page_count': doc.page_count,
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', '')
        }

        all_text = []
        extraction_method = 'PyMuPDF text'

        for page_num in range(doc.page_count):
            page = doc[page_num]

            # Try to get text with better block detection
            page_text = page.get_text(
                'text',  # Use text format
                sort=True  # Sort blocks top-to-bottom, left-to-right
            )

            page_data = {
                'page_number': page_num + 1,
                'text': page_text.strip(),
                'char_count': len(page_text),
                'word_count': len(page_text.split()) if page_text.strip() else 0
            }

            text_data['pages'].append(page_data)
            all_text.append(page_text)

        text_data['full_text'] = '\n\n'.join(all_text)
        text_data['extraction_method'] = extraction_method
        doc.close()

        # If minimal text extracted, try OCR
        if len(text_data['full_text'].strip()) < 500:  # Less than 500 chars
            print("  ⚠️  Limited text extracted, attempting OCR...")
            doc = fitz.open(pdf_path)
            ocr_text = []
            extraction_method = 'PyMuPDF OCR'

            for page_num in range(doc.page_count):
                page = doc[page_num]

                # Higher resolution for better OCR
                mat = fitz.Matrix(2.5, 2.5)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")

                image = Image.open(io.BytesIO(img_data))

                # Use Tesseract with language hints
                page_text = pytesseract.image_to_string(
                    image,
                    lang='eng',
                    config='--psm 1 --oem 3'  # PSM 1 = auto page segmentation, OEM 3 = default
                )

                page_data = {
                    'page_number': page_num + 1,
                    'text': page_text.strip(),
                    'char_count': len(page_text),
                    'word_count': len(page_text.split()) if page_text.strip() else 0,
                    'method': 'OCR'
                }

                text_data['pages'][page_num] = page_data
                ocr_text.append(page_text)

            text_data['full_text'] = '\n\n'.join(ocr_text)
            text_data['extraction_method'] = extraction_method
            doc.close()

    except Exception as e:
        print(f"  ⚠️  Error with PyMuPDF: {e}")
        print("  Falling back to PyPDF2...")

        # Fallback to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_data['metadata'] = {
                    'page_count': len(pdf_reader.pages),
                    'title': pdf_reader.metadata.get('/Title', '') if pdf_reader.metadata else '',
                    'author': pdf_reader.metadata.get('/Author', '') if pdf_reader.metadata else ''
                }

                all_text = []
                extraction_method = 'PyPDF2'

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()

                    page_data = {
                        'page_number': page_num + 1,
                        'text': page_text.strip() if page_text else '',
                        'char_count': len(page_text) if page_text else 0,
                        'word_count': len(page_text.split()) if page_text and page_text.strip() else 0,
                        'method': 'PyPDF2'
                    }

                    text_data['pages'].append(page_data)
                    if page_text:
                        all_text.append(page_text)

                text_data['full_text'] = '\n\n'.join(all_text)
                text_data['extraction_method'] = extraction_method

        except Exception as e2:
            print(f"  ❌ Error with PyPDF2: {e2}")
            return None

    return text_data


def format_output(text_data: Dict, apply_cleaning: bool = True) -> str:
    """Format extracted text with optional cleaning"""
    if not text_data:
        return "No text could be extracted from the PDF."

    # Apply cleaning if requested
    full_text = text_data['full_text']
    cleaning_applied = False

    if apply_cleaning:
        cleaner = PatientRecordOCRCleaner()
        full_text = cleaner.clean_text(full_text)
        cleaning_applied = True

    # Format output
    output = []
    output.append("=" * 70)
    output.append("PATIENT RECORD PDF TEXT EXTRACTION")
    output.append("=" * 70)
    output.append(f"File: {text_data['file_path']}")
    output.append(f"Pages: {text_data['metadata'].get('page_count', 'Unknown')}")
    output.append(f"Extraction method: {text_data['extraction_method']}")

    if cleaning_applied:
        output.append("Text cleaning: Applied (two-layer)")
    else:
        output.append("Text cleaning: Disabled (raw OCR output)")

    if text_data['metadata'].get('title'):
        output.append(f"Title: {text_data['metadata']['title']}")

    output.append("-" * 70)
    output.append("EXTRACTED TEXT:")
    output.append("-" * 70)
    output.append(full_text)

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Extract and clean text from patient record PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract with cleaning (default)
  python patient_record_ocr.py record.pdf

  # Save to specific file with cleaning
  python patient_record_ocr.py record.pdf --output clean_record.txt

  # Extract without cleaning (raw OCR)
  python patient_record_ocr.py record.pdf --no-clean
        """
    )

    parser.add_argument('--input_file', help='Path to the input PDF file')
    parser.add_argument('--output', '-o', help='Output file path (default: input_file.txt)')
    parser.add_argument('--no-clean', action='store_true', help='Skip text cleaning (use raw OCR output)')

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.input_file):
        print(f"❌ Error: File '{args.input_file}' not found.")
        sys.exit(1)

    if not args.input_file.lower().endswith('.pdf'):
        print("❌ Error: Input file must be a PDF file.")
        sys.exit(1)

    print(f"\n📄 Processing PDF: {args.input_file}")
    print("🔍 Extracting text...")

    # Extract text
    text_data = extract_text_from_pdf(args.input_file)

    if not text_data:
        print("❌ Failed to extract text from PDF.")
        sys.exit(1)

    # Format output
    formatted_output = format_output(text_data, apply_cleaning=not args.no_clean)

    # Generate default output filename if not provided
    if not args.output:
        input_path = Path(args.input_file)
        args.output = str(input_path.with_suffix('.txt'))

    # Save output
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        print(f"✅ Extracted and saved to: {args.output}")
        print(f"   Cleaning: {'Applied' if not args.no_clean else 'Disabled'}")
    except Exception as e:
        print(f"❌ Error writing to output file: {e}")
        print("\n📝 Extracted text:")
        print(formatted_output)


if __name__ == "__main__":
    main()
