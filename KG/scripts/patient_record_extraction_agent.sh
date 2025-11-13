#!/bin/bash

# Simple patient record pipeline (run from KG directory)
# Input: PDF file path
# Output: Extracted text + parsed JSON

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate capstone

RECORD_ID="LCD_34106_001"
OUTPUT_DIR="test3"
PDF_INPUT="NCD_LCD_Syn_data/L34106/L34106_Record_001.pdf"
PROMPT_FILE="prompts/Patient_Record_Parser/0.txt"
DATA_DICT="test3/Data_dictionary_L34106.json"

mkdir -p "$OUTPUT_DIR"

echo "========================================="
echo "Step 1: Patient Record OCR"
echo "========================================="
python OCR/patient_record_ocr.py --input_file "$PDF_INPUT" --output "$OUTPUT_DIR/$RECORD_ID.txt"

echo ""
echo "========================================="
echo "Step 2: Patient Record Parsing"
echo "========================================="
python process_patient_record.py \
    --patient_record_pdf "$OUTPUT_DIR/$RECORD_ID.txt" \
    --data_dictionary "$DATA_DICT" \
    --prompt "$PROMPT_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --record-id "$RECORD_ID"

echo ""
echo "========================================="
echo "Results"
echo "========================================="
echo "Extracted text: $OUTPUT_DIR/$RECORD_ID.txt"
echo "Parsed JSON: $OUTPUT_DIR/PatientRecord_$RECORD_ID.json"
echo ""
echo "Content of extracted JSON:"
echo "========================================="
if [ -f "$OUTPUT_DIR/PatientRecord_$RECORD_ID.json" ]; then
    cat "$OUTPUT_DIR/PatientRecord_$RECORD_ID.json"
else
    echo "ERROR: JSON file not found at $OUTPUT_DIR/PatientRecord_$RECORD_ID.json"
fi
