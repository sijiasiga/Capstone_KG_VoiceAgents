#!/bin/bash

# Set the patient record file (change this to plot different patients)
patient_record='test3/PatientRecord_LCD_34106_001.json'

# Extract patient_id from the JSON file
patient_id="LCD_34106_001"
echo "🔄 Processing Patient ID: $patient_id for rule KG..."
echo "📁 Using file: $patient_record"

# Generate the patient rule knowledge graph
python patient_rule_kg.py "$patient_record" \
  --sql-file "test3/SQL_L34106.txt" \
  --policy-file "test3/Policy_L34106.json" \
  --output-file "test3/patient_rule_kg_$patient_id"