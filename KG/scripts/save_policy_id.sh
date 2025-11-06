#!/bin/bash

FILE_DIR="NCD_LCD_Syn_data/L34106/LCD - Percutaneous Vertebral Augmentation (PVA) for Osteoporotic Vertebral Compression Fracture (VCF) (L34106).pdf"
OUTPUT_DIR="test4"

mkdir -p "$OUTPUT_DIR"

POLICY_ID=$(python utils/extract_policy_id.py --file_dir "$FILE_DIR")
python utils/save_policy_id.py --policy-id "$POLICY_ID" --output-dir "$OUTPUT_DIR"
