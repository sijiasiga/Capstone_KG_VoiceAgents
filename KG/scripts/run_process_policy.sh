#!/bin/bash

# Process medical policy: OCR → Extract fields → Extract conditions → Convert to SQL
# Run from KG/ directory

PDF_FILE="NCD_LCD_Syn_data/L34106/LCD - Percutaneous Vertebral Augmentation (PVA) for Osteoporotic Vertebral Compression Fracture (VCF) (L34106).pdf"
OUTPUT_DIR="test4"
INITIAL_DATA_DIC="test1/Data_dictionary.json"
DATAFIELD_PROMPT="prompts/DataField/1.txt"
POLICY_PROMPT="prompts/Policy/1.txt"
SQL_PROMPT="prompts/SQL/1.txt"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Extract policy_id from PDF filename using the utility
POLICY_ID=$(python utils/extract_policy_id.py --file_dir "$PDF_FILE")

echo "Extracted policy_id: $POLICY_ID"
echo ""

echo ""
echo "Saving policy information..."
python utils/save_policy_id.py --policy-id "$POLICY_ID" --output-dir "$OUTPUT_DIR"
echo "✓ Policy information saved"

echo "Step 0: Extracting text from PDF..."
echo "PDF file: $PDF_FILE"
echo ""

# Step 0: Extract text from PDF using OCR
# Save with policy_id in filename
EXTRACTED_TEXT_FILE="$OUTPUT_DIR/Policy_$POLICY_ID.txt"
python OCR/policy_ocr.py --input_file "$PDF_FILE" --output "$EXTRACTED_TEXT_FILE"

if [ ! -f "$EXTRACTED_TEXT_FILE" ]; then
    echo "Error: Failed to extract text from PDF"
    exit 1
fi

echo ""
echo "Step 1-3: Processing extracted policy text..."
echo "Output dir: $OUTPUT_DIR"
echo ""

# Run python script with explicit policy_id
python process_policy.py \
  --policy "$EXTRACTED_TEXT_FILE" \
  --policy-id "$POLICY_ID" \
  --dictionary "$INITIAL_DATA_DIC" \
  --datafield-prompt "$DATAFIELD_PROMPT" \
  --policy-prompt "$POLICY_PROMPT" \
  --sql-prompt "$SQL_PROMPT" \
  --output-dir "$OUTPUT_DIR"

echo ""
echo "Step 4: Generating Knowledge Graph For Policy $POLICY_ID..."
SQL_FILE="$OUTPUT_DIR/SQL_$POLICY_ID.txt"
DATA_DICT_FILE="$OUTPUT_DIR/Data_dictionary_$POLICY_ID.json"

python policy_rule_kg.py \
  --sql "$SQL_FILE" \
  --data-dict "$DATA_DICT_FILE" \
  --policy-id "$POLICY_ID" \
  --output-dir "$OUTPUT_DIR" \
  --plot-path "$OUTPUT_DIR/policy_rule_kg_$POLICY_ID.png"

echo "✓ Policy Knowledge Graph generated"

