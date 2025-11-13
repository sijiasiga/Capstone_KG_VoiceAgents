#!/bin/bash

patient_record="test3/PatientRecord_LCD_34106_001.json"

patient_id="LCD_34106_001"

echo "🔄 Processing Patient ID: $patient_id..."
echo "📁 Using file: $patient_record"

# Generate the patient knowledge graph
python patient_kg.py "$patient_record" \
  --output-file "test3/patient_kg_$patient_id" \
  --db-dir Database \
  --no-show