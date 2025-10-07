#!/usr/bin/env python3
"""
Simple OCR program to extract text from PDF files.
Usage: python pdf_ocr.py <input_pdf_path> [--output <output_file>]
"""

import argparse
import sys
import os
import io
from pathlib import Path

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


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF using multiple methods for better coverage.
    Returns structured text data.
    """
    text_data = {
        'file_path': str(pdf_path),
        'pages': [],
        'full_text': '',
        'metadata': {}
    }
    
    try:
        # Method 1: Try PyMuPDF first (better for text-based PDFs)
        doc = fitz.open(pdf_path)
        text_data['metadata'] = {
            'page_count': doc.page_count,
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', '')
        }
        
        all_text = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text()
            
            page_data = {
                'page_number': page_num + 1,
                'text': page_text.strip(),
                'char_count': len(page_text),
                'word_count': len(page_text.split()) if page_text.strip() else 0
            }
            
            text_data['pages'].append(page_data)
            all_text.append(page_text)
        
        text_data['full_text'] = '\n\n'.join(all_text)
        doc.close()
        
        # If no text extracted, try OCR with PyMuPDF
        if not text_data['full_text'].strip():
            print("No text found, attempting OCR...")
            doc = fitz.open(pdf_path)
            ocr_text = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # Increase resolution
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Use PIL to open image and OCR
                image = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(image)
                
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
            doc.close()
        
    except Exception as e:
        print(f"Error processing PDF with PyMuPDF: {e}")
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
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    
                    page_data = {
                        'page_number': page_num + 1,
                        'text': page_text.strip(),
                        'char_count': len(page_text),
                        'word_count': len(page_text.split()) if page_text.strip() else 0,
                        'method': 'PyPDF2'
                    }
                    
                    text_data['pages'].append(page_data)
                    all_text.append(page_text)
                
                text_data['full_text'] = '\n\n'.join(all_text)
                
        except Exception as e2:
            print(f"Error processing PDF with PyPDF2: {e2}")
            return None
    
    return text_data


def format_output(text_data, output_format='structured'):
    """
    Format the extracted text in a structured way.
    """
    if not text_data:
        return "No text could be extracted from the PDF."
    
    output = []
    output.append("=" * 60)
    output.append(f"PDF TEXT EXTRACTION RESULTS")
    output.append("=" * 60)
    output.append(f"File: {text_data['file_path']}")
    output.append(f"Pages: {text_data['metadata'].get('page_count', 'Unknown')}")
    
    if text_data['metadata'].get('title'):
        output.append(f"Title: {text_data['metadata']['title']}")
    if text_data['metadata'].get('author'):
        output.append(f"Author: {text_data['metadata']['author']}")
    
    # output.append("")
    # output.append("SUMMARY:")
    # output.append(f"Total characters: {len(text_data['full_text'])}")
    # output.append(f"Total words: {len(text_data['full_text'].split())}")
    # output.append("")
    
    if output_format == 'detailed':
        # Show page-by-page breakdown
        for page in text_data['pages']:
            if page['text'].strip():  # Only show pages with content
                output.append(f"--- PAGE {page['page_number']} ---")
                output.append(f"Characters: {page['char_count']}, Words: {page['word_count']}")
                output.append("")
                output.append(page['text'])
                output.append("")
    else:
        # Show full text
        output.append("FULL TEXT:")
        output.append("-" * 40)
        output.append(text_data['full_text'])
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Extract text from PDF files using OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_ocr.py document.pdf
  python pdf_ocr.py document.pdf --output extracted_text.txt
  python pdf_ocr.py document.pdf --format detailed
        """
    )
    
    parser.add_argument('input_file', help='Path to the input PDF file')
    parser.add_argument('--output', '-o', help='Output file path (optional)')
    parser.add_argument('--format', '-f', choices=['structured', 'detailed'], 
                       default='structured', help='Output format (default: structured)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: File '{args.input_file}' not found.")
        sys.exit(1)
    
    # Check if it's a PDF file
    if not args.input_file.lower().endswith('.pdf'):
        print("Error: Input file must be a PDF file.")
        sys.exit(1)
    
    print(f"Processing PDF: {args.input_file}")
    print("Extracting text...")
    
    # Extract text
    text_data = extract_text_from_pdf(args.input_file)
    
    if not text_data:
        print("Failed to extract text from PDF.")
        sys.exit(1)
    
    # Format output
    formatted_output = format_output(text_data, args.format)
    
    # Generate default output filename if not provided
    if not args.output:
        input_path = Path(args.input_file)
        args.output = input_path.with_suffix('.txt')
    
    # Output results
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        print(f"Text extracted and saved to: {args.output}")
    except Exception as e:
        print(f"Error writing to output file: {e}")
        print("\nExtracted text:")
        print(formatted_output)


if __name__ == "__main__":
    main()
