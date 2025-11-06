#!/bin/bash

# Process all medical policies in NCD_LCD_Syn_data directory
# Generates OCR text, data fields, policy conditions, SQL, and knowledge graphs
# Run from KG/ directory

DATA_DIR="NCD_LCD_Syn_data"
OUTPUT_BASE_DIR="Policies_test"
INITIAL_DATA_DIC="test1/Data_dictionary.json"
DATAFIELD_PROMPT="prompts/DataField/1.txt"
POLICY_PROMPT="prompts/Policy/1.txt"
SQL_PROMPT="prompts/SQL/1.txt"

# Create base output directory
mkdir -p "$OUTPUT_BASE_DIR"

echo "========================================"
echo "Processing all policies in $DATA_DIR"
echo "========================================"
echo ""

# Counter for tracking progress
total_policies=0
processed_policies=0
failed_policies=0

# Find all policy PDFs
for policy_dir in "$DATA_DIR"/*/; do
    if [ ! -d "$policy_dir" ]; then
        continue
    fi

    # Find PDF files matching the LCD/NCD policy naming pattern: "LCD - ..." or "NCD - ..."
    pdf_file=$(find "$policy_dir" -maxdepth 1 -name "*.pdf" -type f | grep -E "(LCD|NCD) - " | head -1)

    if [ -z "$pdf_file" ]; then
        continue
    fi

    policy_name=$(basename "$policy_dir")

    echo "Processing: $policy_name"
    echo "PDF: $pdf_file"

    # Extract policy_id
    POLICY_ID=$(python utils/extract_policy_id.py --file_dir "$pdf_file" 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo "❌ Failed to extract policy_id from: $policy_name"
        ((failed_policies++))
        echo ""
        continue
    fi

    OUTPUT_DIR="$OUTPUT_BASE_DIR/Policy_$POLICY_ID"
    mkdir -p "$OUTPUT_DIR"

    echo "Policy ID: $POLICY_ID"

    # Step 0: Extract text from PDF using OCR
    EXTRACTED_TEXT_FILE="$OUTPUT_DIR/Policy_$POLICY_ID.txt"
    python OCR/policy_ocr.py --input_file "$pdf_file" --output "$EXTRACTED_TEXT_FILE" 2>/dev/null

    if [ ! -f "$EXTRACTED_TEXT_FILE" ]; then
        echo "❌ Failed to extract text from PDF"
        ((failed_policies++))
        echo ""
        continue
    fi

    # Step 1-3: Process policy
    python process_policy.py \
      --policy "$EXTRACTED_TEXT_FILE" \
      --policy-id "$POLICY_ID" \
      --dictionary "$INITIAL_DATA_DIC" \
      --datafield-prompt "$DATAFIELD_PROMPT" \
      --policy-prompt "$POLICY_PROMPT" \
      --sql-prompt "$SQL_PROMPT" \
      --output-dir "$OUTPUT_DIR" 2>/dev/null

    if [ $? -ne 0 ]; then
        echo "❌ Failed to process policy"
        ((failed_policies++))
        echo ""
        continue
    fi

    # Step 4: Generate Knowledge Graph
    SQL_FILE="$OUTPUT_DIR/SQL_$POLICY_ID.txt"
    DATA_DICT_FILE="$OUTPUT_DIR/Data_dictionary_$POLICY_ID.json"

    if [ ! -f "$SQL_FILE" ] || [ ! -f "$DATA_DICT_FILE" ]; then
        echo "❌ Required files not found for KG generation"
        ((failed_policies++))
        echo ""
        continue
    fi

    python policy_rule_kg.py \
      --sql "$SQL_FILE" \
      --data-dict "$DATA_DICT_FILE" \
      --policy-id "$POLICY_ID" \
      --output-dir "$OUTPUT_DIR" \
      --plot-path "$OUTPUT_DIR/policy_rule_kg_$POLICY_ID.png" 2>/dev/null

    if [ $? -ne 0 ]; then
        echo "❌ Failed to generate knowledge graph"
        ((failed_policies++))
        echo ""
        continue
    fi

    # Save policy information
    python utils/save_policy_info.py --policy-id "$POLICY_ID" --output-dir "$OUTPUT_DIR" 2>/dev/null

    echo "✓ Successfully processed: $POLICY_ID"
    ((processed_policies++))
    echo ""
    ((total_policies++))
done

echo "========================================"
echo "Summary"
echo "========================================"
echo "Total policies found: $total_policies"
echo "Successfully processed: $processed_policies"
echo "Failed: $failed_policies"
echo "Output directory: $OUTPUT_BASE_DIR"
echo ""
