# Medical Record Knowledge Graph Streamlit App

A Streamlit web application for processing medical records and generating knowledge graphs.

## Features

- **PDF Upload**: Upload medical record PDF files
- **Text Extraction**: Automatic OCR text extraction from PDFs
- **Data Parsing**: Extract structured patient data from medical records
- **Knowledge Graph Generation**: Create three types of knowledge graphs:
  - Policy Knowledge Graph
  - Patient Knowledge Graph  
  - Patient Rule Knowledge Graph
- **File Organization**: Automatically organize files in patient-specific folders
- **Interactive Visualization**: View and download generated knowledge graphs

## Installation

1. Install required packages:
```bash
pip install -r streamlit_requirements.txt
```

2. Make sure you have the required system dependencies:
   - Tesseract OCR (for PDF text extraction)
   - Graphviz (optional, for hierarchical layouts)

## Usage

1. Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

2. Open your browser to the provided URL (usually `http://localhost:8501`)

3. Upload a medical record PDF file

4. Configure processing options:
   - Choose which knowledge graphs to generate
   - Enable/disable auto-processing

5. Click "Process Medical Record" or enable "Auto Process"

6. View the generated knowledge graphs and download them

## File Structure

The app creates a `patient_data/` directory with subdirectories for each patient:
```
patient_data/
└── patient_{patient_id}/
    ├── {original_pdf_name}.pdf
    ├── {original_pdf_name}.txt
    ├── Patient_data_dictionary_{patient_id}.json
    ├── policy_rule_kg.png
    ├── patient_kg.png
    ├── patient_rule_kg.png
    └── pat_{patient_id}_pol_CGSURG83.json
```

## Dependencies

- **Streamlit**: Web application framework
- **PyPDF2/PyMuPDF**: PDF processing
- **pytesseract**: OCR text extraction
- **Pillow**: Image processing
- **networkx**: Graph creation and manipulation
- **matplotlib**: Static graph visualization
- **plotly**: Interactive graph visualization (optional)

## Troubleshooting

- **OCR Issues**: Ensure Tesseract is installed and in your PATH
- **Import Errors**: Make sure all required Python packages are installed
- **File Not Found**: Ensure the KG directory structure is correct
- **Permission Errors**: Check write permissions for the patient_data directory

## Notes

- The app uses test policy files from the `KG/test/` directory
- Patient ID is extracted from the PDF filename
- All processing is done locally - no data is sent to external services
- Generated files are saved in the local file system
