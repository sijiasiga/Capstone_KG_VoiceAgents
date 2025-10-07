#!/bin/bash

# Generate policy rule knowledge graph
python generate_policy_rule_kg.py --sql test1/Policy_CGSURG83/SQL_CGSURG83.txt --data-dict test1/Policy_CGSURG83/Data_dictionary_CGSURG83.json --output-dir test1/Policy_CGSURG83 --plot-path test1/Policy_CGSURG83/policy_rule_kg.png




#!/bin/bash

# Script to generate patient rule knowledge graphs for all patient data dictionary files
# Based on plot_patient_rule_kg.sh but iterates through all files and uses patient_id

# Loop through all Patient_data_dictionary*.json files
for patient_file in test1/Patient_data_dictionary/Patient_data_dictionary*.json; do
    if [ -f "$patient_file" ]; then
        # Extract patient_id from the JSON file
        patient_id=$(python -c "import json; data=json.load(open('$patient_file')); print(data.get('patient_id', 'unknown'))")
        
        echo "🔄 Processing Patient ID: $patient_id for rule KG..."
        
        # Generate the patient rule knowledge graph and save to Patient_Rule_KG directory
        python patient_rule_kg.py "$patient_file" test1/Policy_CGSURG83/SQL_CGSURG83.txt test1/Policy_CGSURG83/Policy_CGSURG83.json --policy-id CGSURG83 --output-file "test1/Patient_Rule_KG/patient_rule_kg_$patient_id" --compliance-dir test1/Patient_Rule_KG --no-show
        
        if [ $? -eq 0 ]; then
            echo "✅ Successfully generated patient_rule_kg_$patient_id"
        else
            echo "❌ Failed to generate patient_rule_kg_$patient_id"
        fi
    fi
done

echo "🎉 Patient rule knowledge graph generation complete!"


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

