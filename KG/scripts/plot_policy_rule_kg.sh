#!/bin/bash

# Generate policy rule knowledge graph
# python generate_policy_rule_kg.py --sql test1/Policy_CGSURG83/SQL_CGSURG83.txt --data-dict test1/Policy_CGSURG83/Data_dictionary_CGSURG83.json --output-dir test1/Policy_CGSURG83 --plot-path test1/Policy_CGSURG83/policy_rule_kg.png

sql_dir="test2/SQL_L34106.txt"
data_dict_dir="test2/Data_dictionary_L34106.json"
output_dir="test2"

python generate_policy_rule_kg.py \
--sql $sql_dir \
--data-dict $data_dict_dir \
--output-dir $output_dir