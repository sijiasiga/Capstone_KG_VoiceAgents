#!/bin/bash

patient_record='test1/Patient_data_dictionary/Patient_data_dictionary_8472202544.json'

patient_id=$(python -c "import json; data=json.load(open('$patient_record')); print(data.get('patient_id', 'unknown'))")

echo "🔄 Processing Patient ID: $patient_id..."
echo "📁 Using file: $patient_record"

# Generate the patient knowledge graph
python patient_kg.py "$patient_record" \
  --output-file "test1/Patient_KG/patient_kg_$patient_id" \
  --db-dir Database \
  --no-show