#!/bin/bash

# Run Streamlit app with capstone conda environment

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate capstone environment
source activate capstone

# Run streamlit
echo "🚀 Starting Streamlit with capstone environment..."
echo "📍 Directory: $SCRIPT_DIR"
echo ""

cd "$SCRIPT_DIR"
streamlit run streamlit_final.py

