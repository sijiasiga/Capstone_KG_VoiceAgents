#!/bin/bash

# Script to generate patient knowledge graphs for all patient data dictionary files
# Based on plot_patient_kg.sh but iterates through all files and uses patient_id

# Loop through all Patient_data_dictionary*.json files
for patient_file in test1/Patient_data_dictionary/Patient_data_dictionary*.json; do
    if [ -f "$patient_file" ]; then
        # Extract patient_id from the JSON file
        patient_id=$(python -c "import json; data=json.load(open('$patient_file')); print(data.get('patient_id', 'unknown'))")
        
        echo "🔄 Processing Patient ID: $patient_id..."
        
        # Generate the patient knowledge graph and save to Patient_KG directory
        python patient_kg.py "$patient_file" --output-file "test1/Patient_KG/patient_kg_$patient_id" --no-show
        
        if [ $? -eq 0 ]; then
            echo "✅ Successfully generated patient_kg_$patient_id"
        else
            echo "❌ Failed to generate patient_kg_$patient_id"
        fi
    fi
done

echo "🎉 Patient knowledge graph generation complete!"
