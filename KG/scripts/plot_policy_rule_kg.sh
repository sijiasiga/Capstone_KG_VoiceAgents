#!/bin/bash

# Generate policy rule knowledge graph
python generate_policy_rule_kg.py --sql test1/Policy_CGSURG83/SQL_CGSURG83.txt --data-dict test1/Policy_CGSURG83/Data_dictionary_CGSURG83.json --output-dir test1/Policy_CGSURG83 --plot-path test1/Policy_CGSURG83/policy_rule_kg.png
