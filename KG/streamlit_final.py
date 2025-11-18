#!/usr/bin/env python3
"""
Medical Record Knowledge Graph Streamlit Application - Extended Version

A Streamlit app for processing medical records and policies, generating knowledge graphs.

Pages:
1. Medical Records - Process patient medical records
2. Policy Conversion - Convert medical policies to structured formats and KG

Author: AI Assistant
"""

import streamlit as st
import os
import json
import tempfile
import subprocess
import sys
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import shutil

# Add the KG directory to Python path
kg_dir = Path(__file__).parent
sys.path.insert(0, str(kg_dir))

# Import our modules
try:
    from OCR.pdf_ocr import extract_text_from_pdf, format_output
    from OCR.medical_record_parser import MedicalRecordParser, parse_medical_record_file
    from policy_rule_kg import PolicyRuleKGGenerator
    from policy_rule_kg_interactive import PolicyRuleKGGenerator_WithInteractive
    from patient_kg import PatientKGVisualizer
    from patient_rule_kg import PatientRuleKGVisualizer
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Medical Record & Policy KG Generator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def get_database_path() -> str:
    """Get the path to the policy database."""
    return str(kg_dir / "Database" / "policy_CGSURG83.db")

def clean_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame by removing duplicate columns and handling data issues."""
    if df is None or df.empty:
        return df

    # Remove duplicate columns (keep first occurrence)
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()]

    return df

def check_database_duplicates() -> Dict[str, Any]:
    """Check for duplicate patients in the database."""
    try:
        db_path = get_database_path()
        if not os.path.exists(db_path):
            return {"error": "Database not found"}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for duplicate patient_ids
        cursor.execute("""
            SELECT patient_id, COUNT(*) as count
            FROM patients
            GROUP BY patient_id
            HAVING COUNT(*) > 1
        """)
        duplicate_patients = cursor.fetchall()

        # Get total patient count
        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = cursor.fetchone()[0]

        # Get unique patient count
        cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patients")
        unique_patients = cursor.fetchone()[0]

        conn.close()

        return {
            "total_patients": total_patients,
            "unique_patients": unique_patients,
            "duplicate_patients": duplicate_patients,
            "has_duplicates": len(duplicate_patients) > 0
        }
    except Exception as e:
        return {"error": str(e)}

def delete_patient_by_id(patient_id: str) -> bool:
    """Delete a specific patient record from the database."""
    try:
        db_path = get_database_path()
        if not os.path.exists(db_path):
            st.error("Database not found")
            return False

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if patient exists
        cursor.execute("SELECT COUNT(*) FROM patients WHERE patient_id = ?", (patient_id,))
        count = cursor.fetchone()[0]

        if count == 0:
            st.warning(f"Patient {patient_id} not found in database")
            conn.close()
            return False

        # Delete the patient
        cursor.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
        conn.commit()
        conn.close()

        return True
    except Exception as e:
        st.error(f"Error deleting patient: {e}")
        return False

def remove_duplicates_from_database() -> bool:
    """Remove duplicate patients from the database, keeping only the latest record."""
    try:
        db_path = get_database_path()
        if not os.path.exists(db_path):
            st.error("Database not found")
            return False

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check table structure
        cursor.execute("PRAGMA table_info(patients)")
        columns = cursor.fetchall()

        # Get all duplicate patient_ids
        cursor.execute("""
            SELECT patient_id, COUNT(*) as count
            FROM patients
            GROUP BY patient_id
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()

        if not duplicates:
            conn.close()
            return True

        # Get all records and create a unique set
        cursor.execute("SELECT * FROM patients")
        all_records = cursor.fetchall()

        # Get column names
        column_names = [col[1] for col in columns]

        # Create a dictionary to track unique patients
        unique_patients = {}
        duplicates_removed = 0

        for record in all_records:
            record_dict = dict(zip(column_names, record))
            patient_id = record_dict.get('patient_id')

            if patient_id not in unique_patients:
                unique_patients[patient_id] = record
            else:
                duplicates_removed += 1

        if duplicates_removed == 0:
            conn.close()
            return True

        # Clear the table
        cursor.execute("DELETE FROM patients")

        # Insert only unique records
        for patient_id, record in unique_patients.items():
            placeholders = ','.join(['?' for _ in record])
            cursor.execute(f"INSERT INTO patients VALUES ({placeholders})", record)

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        st.error(f"Error removing duplicates: {e}")
        return False

def add_patient_to_database(patient_data: Dict[str, Any]) -> bool:
    """Add patient data to the database with proper duplicate handling."""
    try:
        db_path = get_database_path()
        if not os.path.exists(db_path):
            st.error(f"Database not found: {db_path}")
            return False

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        patient_id = patient_data.get('patient_id')
        if not patient_id:
            st.error("Patient ID is required")
            conn.close()
            return False

        # First, delete any existing records for this patient_id
        cursor.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))

        # Get field names and values from patient data
        field_names = list(patient_data.keys())
        values = list(patient_data.values())

        # Insert the new record
        placeholders = ','.join(['?' for _ in field_names])
        insert_sql = f"INSERT INTO patients ({','.join(field_names)}) VALUES ({placeholders})"

        cursor.execute(insert_sql, values)
        conn.commit()
        conn.close()

        return True
    except Exception as e:
        st.error(f"Error adding patient to database: {e}")
        return False

def get_all_patients() -> Optional[pd.DataFrame]:
    """Get all patient data from the database, automatically removing duplicates first."""
    try:
        # First, remove duplicates automatically (silent)
        remove_duplicates_from_database()

        db_path = get_database_path()
        if not os.path.exists(db_path):
            st.error(f"Database not found: {db_path}")
            return None

        conn = sqlite3.connect(db_path)
        query = "SELECT * FROM patients"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Clean the DataFrame
        df = clean_dataframe_columns(df)

        return df
    except Exception as e:
        st.error(f"Error retrieving patient data: {e}")
        return None

def run_policy_sql_filter() -> Optional[pd.DataFrame]:
    """Run the policy SQL filter on the database."""
    try:
        db_path = get_database_path()
        sql_path = kg_dir / "test1" / "Policy_CGSURG83" / "SQL_CGSURG83.txt"

        if not os.path.exists(db_path):
            st.error(f"Database not found: {db_path}")
            return None

        if not os.path.exists(sql_path):
            st.error(f"SQL file not found: {sql_path}")
            return None

        # Load SQL query
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_query = f.read().strip()

        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()

        # Clean the DataFrame
        df = clean_dataframe_columns(df)

        return df
    except Exception as e:
        st.error(f"Error running SQL filter: {e}")
        return None

def display_node_info_sidebar(nodes: List[Dict]) -> None:
    """Display node information selector in sidebar."""
    st.sidebar.markdown("### 📌 Node Information")
    st.sidebar.markdown("---")

    if not nodes:
        st.sidebar.info("No nodes available")
        return

    # Create list of node labels for selection
    node_options = []
    node_map = {}

    for node in nodes:
        node_id = node.get('id', '')
        label = node.get('label', node_id)
        node_options.append(f"{label} ({node_id})")
        node_map[f"{label} ({node_id})"] = node

    # Select node
    selected_option = st.sidebar.selectbox(
        "Select a node to view details:",
        options=node_options,
        key="node_selector"
    )

    if selected_option:
        selected_node = node_map[selected_option]

        # Display node details
        st.sidebar.markdown("**Node Details:**")
        st.sidebar.markdown(f"**ID:** `{selected_node.get('id', 'N/A')}`")
        st.sidebar.markdown(f"**Type:** `{selected_node.get('type', 'N/A')}`")

        if selected_node.get('label'):
            st.sidebar.markdown(f"**Label:** {selected_node.get('label')}")

        if selected_node.get('description'):
            st.sidebar.markdown(f"**Description:** {selected_node.get('description')}")

        if selected_node.get('field_name'):
            st.sidebar.markdown(f"**Field Name:** `{selected_node.get('field_name')}`")

        if selected_node.get('operator'):
            st.sidebar.markdown(f"**Operator:** `{selected_node.get('operator')}`")

        if selected_node.get('value'):
            st.sidebar.markdown(f"**Value:** `{selected_node.get('value')}`")

        if selected_node.get('section'):
            st.sidebar.markdown(f"**Section:** `{selected_node.get('section')}`")

        if selected_node.get('condition_type'):
            st.sidebar.markdown(f"**Condition Type:** `{selected_node.get('condition_type')}`")


def create_patient_folder(patient_id: str, base_dir: str = "patient_data") -> str:
    """Create a folder for the patient and return the path."""
    patient_dir = Path(base_dir) / f"patient_{patient_id}"
    patient_dir.mkdir(parents=True, exist_ok=True)
    return str(patient_dir)

def save_uploaded_file(uploaded_file, patient_dir: str) -> str:
    """Save uploaded file to patient directory."""
    file_path = Path(patient_dir) / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)

def run_pdf_ocr(pdf_path: str, patient_dir: str) -> str:
    """Run PDF OCR to extract text."""
    txt_path = Path(patient_dir) / f"{Path(pdf_path).stem}.txt"

    try:
        # Extract text using our OCR module
        text_data = extract_text_from_pdf(pdf_path)
        if not text_data:
            raise Exception("Failed to extract text from PDF")

        # Format and save output
        formatted_output = format_output(text_data, 'structured')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(formatted_output)

        return str(txt_path)
    except Exception as e:
        st.error(f"Error in PDF OCR: {e}")
        return None

def parse_medical_record(txt_path: str, patient_dir: str) -> Optional[Dict[str, Any]]:
    """Parse medical record to extract structured data."""
    try:
        # Read the text file
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Parse using our medical record parser
        parser = MedicalRecordParser(text)
        patient_data = parser.parse()

        # Save the parsed data
        patient_id = patient_data.get('patient_id', 'unknown')
        json_path = Path(patient_dir) / f"Patient_data_dictionary_{patient_id}.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(patient_data, f, indent=2)

        return patient_data
    except Exception as e:
        st.error(f"Error parsing medical record: {e}")
        return None

def generate_policy_kg(patient_dir: str, show_plot: bool = True) -> Optional[str]:
    """Generate policy knowledge graph."""
    try:
        # Use test data for policy KG
        sql_path = kg_dir / "test1" / "Policy_CGSURG83" / "SQL_CGSURG83.txt"
        data_dict_path = kg_dir / "test1" / "Policy_CGSURG83" / "Data_dictionary_CGSURG83.json"

        if not sql_path.exists() or not data_dict_path.exists():
            st.warning("Policy files not found. Using default paths.")
            return None

        # Generate policy KG
        generator = PolicyRuleKGGenerator(
            sql_path=str(sql_path),
            data_dictionary_path=str(data_dict_path),
            output_dir=patient_dir
        )

        nodes, edges = generator.generate()

        # Save JSON files
        nodes_path, edges_path = generator.save_json()

        # Generate plot
        plot_path = Path(patient_dir) / "policy_rule_kg.png"
        generator.plot(output_path=str(plot_path), show=show_plot)

        return str(plot_path)
    except Exception as e:
        st.error(f"Error generating policy KG: {e}")
        return None

def generate_patient_kg(patient_data: Dict[str, Any], patient_dir: str, show_plot: bool = True) -> Optional[str]:
    """Generate patient knowledge graph."""
    try:
        # Create visualizer
        visualizer = PatientKGVisualizer(patient_data)
        visualizer.build_graph()

        # Generate plot
        plot_path = Path(patient_dir) / "patient_kg"
        visualizer.create_matplotlib_visualization(
            output_file=str(plot_path),
            no_show=not show_plot
        )

        # The visualizer adds .png extension, so update the path
        plot_path = Path(patient_dir) / "patient_kg.png"

        return str(plot_path)
    except Exception as e:
        st.error(f"Error generating patient KG: {e}")
        return None

def generate_patient_rule_kg(patient_data: Dict[str, Any], patient_dir: str, show_plot: bool = True) -> Optional[str]:
    """Generate patient rule knowledge graph."""
    try:
        # Load required files
        sql_path = kg_dir / "test1" / "Policy_CGSURG83" / "SQL_CGSURG83.txt"
        policy_path = kg_dir / "test1" / "Policy_CGSURG83" / "Policy_CGSURG83.json"

        if not sql_path.exists() or not policy_path.exists():
            st.warning("Policy files not found for patient rule KG.")
            return None

        # Load data
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_text = f.read()

        with open(policy_path, 'r', encoding='utf-8') as f:
            policy_data = json.load(f)

        # Create visualizer
        visualizer = PatientRuleKGVisualizer(patient_data, sql_text, policy_data)
        visualizer.parse_and_evaluate_conditions()
        visualizer.apply_logical_operators()
        visualizer.build_knowledge_graph()

        # Generate plot
        plot_path = Path(patient_dir) / "patient_rule_kg"
        visualizer.create_visualization(
            output_file=str(plot_path),
            no_show=not show_plot
        )

        # The visualizer adds .png extension, so update the path
        plot_path = Path(patient_dir) / "patient_rule_kg.png"

        # Generate compliance report
        patient_id = patient_data.get('patient_id', 'unknown')
        compliance_path = visualizer.generate_compliance_report(
            patient_id, "CGSURG83", patient_dir
        )

        return str(plot_path)
    except Exception as e:
        st.error(f"Error generating patient rule KG: {e}")
        return None

def medical_record_page():
    """Medical Record Processing Page."""

    # Header
    st.markdown('<h1 class="main-header">🏥 Medical Record Knowledge Graph Generator</h1>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("📋 Processing Options")

    # File upload
    st.markdown('<h2 class="section-header">📁 Upload Medical Record</h2>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload a medical record PDF file to process"
    )

    if uploaded_file is not None:
        # Display file info
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        st.info(f"📊 File size: {uploaded_file.size:,} bytes")

        # Processing options
        st.markdown('<h2 class="section-header">⚙️ Processing Configuration</h2>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            show_policy_kg = st.checkbox("Show Policy KG", value=True, help="Display policy knowledge graph")
            show_patient_kg = st.checkbox("Show Patient KG", value=True, help="Display patient knowledge graph")

        with col2:
            show_patient_rule_kg = st.checkbox("Show Patient Rule KG", value=True, help="Display patient rule knowledge graph")
            auto_process = st.checkbox("Auto Process", value=True, help="Automatically process after upload")

        # Process button
        if st.button("🚀 Process Medical Record", type="primary") or auto_process:

            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # Step 1: Create temporary folder for initial processing
                status_text.text("📁 Creating temporary processing folder...")
                progress_bar.progress(5)

                temp_dir = create_patient_folder("temp_processing")

                # Step 2: Save uploaded file to temp folder
                status_text.text("💾 Saving uploaded file...")
                progress_bar.progress(10)

                pdf_path = save_uploaded_file(uploaded_file, temp_dir)
                st.success(f"✅ PDF saved: {pdf_path}")

                # Step 3: Extract text from PDF
                status_text.text("🔍 Extracting text from PDF...")
                progress_bar.progress(25)

                txt_path = run_pdf_ocr(pdf_path, temp_dir)
                if txt_path:
                    st.success(f"✅ Text extracted: {txt_path}")
                else:
                    st.error("❌ Failed to extract text from PDF")
                    return

                # Step 4: Parse medical record
                status_text.text("📋 Parsing medical record...")
                progress_bar.progress(40)

                patient_data = parse_medical_record(txt_path, temp_dir)
                if patient_data:
                    st.success("✅ Medical record parsed successfully")

                    # Display extracted data
                    with st.expander("📊 Extracted Patient Data", expanded=True):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Basic Info:**")
                            st.write(f"- Patient ID: {patient_data.get('patient_id', 'N/A')}")
                            st.write(f"- Age: {patient_data.get('patient_age', 'N/A')}")
                            st.write(f"- BMI: {patient_data.get('patient_bmi', 'N/A')}")

                        with col2:
                            st.write("**Medical Status:**")
                            st.write(f"- Comorbidities: {'Yes' if patient_data.get('comorbidity_flag') else 'No'}")
                            st.write(f"- Medical Clearance: {'Yes' if patient_data.get('preop_medical_clearance') else 'No'}")
                            st.write(f"- Psych Clearance: {'Yes' if patient_data.get('preop_psych_clearance') else 'No'}")

                        st.write("**Codes:**")
                        st.write(f"- CPT Code: {patient_data.get('procedure_code_CPT', 'N/A')}")
                        st.write(f"- ICD-10 Diagnosis: {patient_data.get('diagnosis_code_ICD10', 'N/A')}")
                        st.write(f"- ICD-10 Procedure: {patient_data.get('procedure_code_ICD10PCS', 'N/A')}")
                else:
                    st.error("❌ Failed to parse medical record")
                    return

                # Step 5: Extract patient ID and create proper folder
                status_text.text("📁 Creating patient-specific folder...")
                progress_bar.progress(50)

                patient_id = patient_data.get('patient_id', 'unknown_patient')
                if not patient_id or patient_id == 'unknown_patient':
                    # Fallback to filename if no patient ID found
                    patient_id = Path(uploaded_file.name).stem
                    if not patient_id or patient_id == "MR_2":
                        patient_id = "unknown_patient"

                # Create patient-specific folder
                patient_dir = create_patient_folder(patient_id)
                st.success(f"✅ Patient folder created: {patient_dir}")

                # Step 6: Move files from temp folder to patient folder
                status_text.text("📂 Organizing files...")
                progress_bar.progress(55)

                # Move PDF file
                final_pdf_path = Path(patient_dir) / uploaded_file.name
                shutil.move(pdf_path, final_pdf_path)

                # Move text file
                final_txt_path = Path(patient_dir) / f"{Path(uploaded_file.name).stem}.txt"
                shutil.move(txt_path, final_txt_path)

                # Move JSON file
                json_file = Path(temp_dir) / f"Patient_data_dictionary_{patient_data.get('patient_id', 'unknown')}.json"
                if json_file.exists():
                    final_json_path = Path(patient_dir) / f"Patient_data_dictionary_{patient_id}.json"
                    shutil.move(str(json_file), str(final_json_path))

                # Clean up temp folder
                shutil.rmtree(temp_dir)

                st.success("✅ Files organized in patient folder")

                # Step 6.5: Add patient to database
                status_text.text("💾 Adding patient to database...")
                progress_bar.progress(58)

                if add_patient_to_database(patient_data):
                    st.success("✅ Patient added to database")
                else:
                    st.warning("⚠️ Failed to add patient to database")

                # Step 7: Generate knowledge graphs
                status_text.text("🎨 Generating knowledge graphs...")
                progress_bar.progress(60)

                generated_plots = {}

                # Policy KG
                if show_policy_kg:
                    with st.spinner("Generating Policy KG..."):
                        policy_plot = generate_policy_kg(patient_dir, show_plot=False)
                        if policy_plot:
                            generated_plots["Policy KG"] = policy_plot
                            st.success("✅ Policy KG generated")
                    progress_bar.progress(70)

                # Patient KG
                if show_patient_kg:
                    with st.spinner("Generating Patient KG..."):
                        patient_plot = generate_patient_kg(patient_data, patient_dir, show_plot=False)
                        if patient_plot:
                            generated_plots["Patient KG"] = patient_plot
                            st.success("✅ Patient KG generated")
                    progress_bar.progress(80)

                # Patient Rule KG
                if show_patient_rule_kg:
                    with st.spinner("Generating Patient Rule KG..."):
                        patient_rule_plot = generate_patient_rule_kg(patient_data, patient_dir, show_plot=False)
                        if patient_rule_plot:
                            generated_plots["Patient Rule KG"] = patient_rule_plot
                            st.success("✅ Patient Rule KG generated")
                    progress_bar.progress(90)

                progress_bar.progress(100)
                status_text.text("✅ Processing complete!")

                # Display results
                st.markdown('<h2 class="section-header">📊 Generated Knowledge Graphs</h2>', unsafe_allow_html=True)

                if generated_plots:
                    # Create tabs for different plots
                    tab_names = list(generated_plots.keys())
                    tabs = st.tabs(tab_names)

                    for i, (plot_name, plot_path) in enumerate(generated_plots.items()):
                        with tabs[i]:
                            st.subheader(f"{plot_name}")

                            if os.path.exists(plot_path):
                                st.image(plot_path, use_container_width=True)

                                # Download button
                                with open(plot_path, "rb") as file:
                                    st.download_button(
                                        label=f"📥 Download {plot_name}",
                                        data=file.read(),
                                        file_name=os.path.basename(plot_path),
                                        mime="image/png"
                                    )
                            else:
                                st.error(f"Plot file not found: {plot_path}")
                else:
                    st.warning("No knowledge graphs were generated.")

                # File browser
                st.markdown('<h2 class="section-header">📁 Generated Files</h2>', unsafe_allow_html=True)

                if st.button("📂 Open Patient Folder"):
                    st.info(f"Patient files are saved in: {patient_dir}")

                    # List files in patient directory
                    patient_files = list(Path(patient_dir).glob("*"))
                    if patient_files:
                        st.write("**Files in patient folder:**")
                        for file_path in sorted(patient_files):
                            file_size = file_path.stat().st_size
                            st.write(f"- {file_path.name} ({file_size:,} bytes)")
                    else:
                        st.write("No files found in patient folder.")

            except Exception as e:
                st.error(f"❌ Error during processing: {e}")
                progress_bar.progress(0)
                status_text.text("❌ Processing failed")

    else:
        # Instructions when no file is uploaded
        st.markdown("""
        <div class="info-box">
        <h3>📋 How to use this application:</h3>
        <ol>
            <li><strong>Upload a PDF:</strong> Click the file uploader above to select a medical record PDF</li>
            <li><strong>Configure options:</strong> Choose which knowledge graphs to generate</li>
            <li><strong>Process:</strong> Click "Process Medical Record" or enable "Auto Process"</li>
            <li><strong>View results:</strong> Examine the generated knowledge graphs and download them</li>
        </ol>

        <h4>🎯 What this app does:</h4>
        <ul>
            <li>Extracts text from medical record PDFs using OCR</li>
            <li>Parses structured patient data from the text</li>
            <li>Generates three types of knowledge graphs:
                <ul>
                    <li><strong>Policy KG:</strong> Shows policy rules and conditions</li>
                    <li><strong>Patient KG:</strong> Visualizes patient data and attributes</li>
                    <li><strong>Patient Rule KG:</strong> Compares patient data against policy rules</li>
                </ul>
            </li>
            <li>Organizes all files in a patient-specific folder</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

def policy_conversion_page():
    """Policy Conversion Page - Upload policy PDF and convert to structured format."""

    # Header
    st.markdown('<h1 class="main-header">📋 Policy Conversion System</h1>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <h4>📖 About Policy Conversion</h4>
    <p>This tool converts medical policy PDFs into structured formats using AI agents:</p>
    <ul>
        <li><strong>OCR Agent:</strong> Extracts text from policy PDF</li>
        <li><strong>DataField Agent:</strong> Identifies and extracts data fields from policy text</li>
        <li><strong>Policy Agent:</strong> Extracts policy conditions and restrictions</li>
        <li><strong>SQL Agent:</strong> Converts policy rules to SQL query format</li>
    </ul>
    <p>All generated files are organized in <code>Run_Time_Policy/{policy_id}/</code></p>
    </div>
    """, unsafe_allow_html=True)

    # File upload
    st.markdown('<h2 class="section-header">📁 Upload Policy PDF</h2>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a policy PDF file",
        type="pdf",
        help="Upload a medical policy PDF to convert",
        key="policy_upload"
    )

    if uploaded_file is not None:
        # Display file info
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        st.info(f"📊 File size: {uploaded_file.size:,} bytes")

        # Process button
        if st.button("🚀 Convert Policy", type="primary"):

            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # Step 0: Extract policy ID from filename
                from utils.extract_policy_id import extract_policy_id_from_filename
                from utils.save_policy_id import save_policy_info

                status_text.text("📝 Extracting policy ID...")
                progress_bar.progress(8)

                # Extract policy ID from filename
                try:
                    policy_id = extract_policy_id_from_filename(uploaded_file.name)
                    st.info(f"📝 Policy ID extracted: {policy_id}")
                except Exception as e:
                    st.warning(f"⚠️ Could not extract policy ID: {e}")
                    st.info("Using filename as fallback...")
                    policy_id = Path(uploaded_file.name).stem.replace(' ', '_')

                # Step 1: Create policy folder in Run_Time_Policy
                status_text.text("📁 Creating policy folder...")
                progress_bar.progress(10)

                policy_base_dir = kg_dir / "Run_Time_Policy"
                policy_base_dir.mkdir(exist_ok=True)

                policy_dir = policy_base_dir / policy_id
                policy_dir.mkdir(exist_ok=True)

                st.success(f"✅ Policy folder created: {policy_dir}")

                # Save policy information
                status_text.text("💾 Saving policy information...")
                progress_bar.progress(12)

                try:
                    info_path = save_policy_info(policy_id, str(policy_dir))
                    st.success(f"✅ Policy info saved: {info_path}")
                except Exception as e:
                    st.warning(f"⚠️ Could not save policy info: {e}")

                # Step 2: Save uploaded PDF directly to policy dir
                status_text.text("💾 Saving policy PDF...")
                progress_bar.progress(15)

                pdf_path = policy_dir / uploaded_file.name
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.success(f"✅ PDF saved: {pdf_path}")

                # Step 3: Run OCR to extract text
                status_text.text("🔍 Running OCR on policy PDF...")
                progress_bar.progress(25)

                # Import policy OCR module
                sys.path.insert(0, str(kg_dir / "OCR"))
                try:
                    from policy_ocr import extract_text_from_pdf as extract_policy_text, format_output as format_policy_output
                except ImportError:
                    st.error("Failed to import policy_ocr module")
                    return

                # Extract text
                text_data = extract_policy_text(str(pdf_path))
                if not text_data:
                    st.error("❌ Failed to extract text from policy PDF")
                    return

                # Format and save (with policy_id in filename)
                formatted_output = format_policy_output(text_data, True)  # Apply cleaning
                # Use the format: Policy_{policy_id}.txt (matching the bash script)
                txt_path = policy_dir / f"Policy_{policy_id}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)

                st.success(f"✅ OCR complete: {txt_path}")

                # Display extracted text preview
                with st.expander("📄 View Extracted Text (Preview)", expanded=False):
                    preview_text = text_data['full_text'][:2000]  # First 2000 chars
                    st.text_area("Extracted Text", preview_text, height=200)
                    if len(text_data['full_text']) > 2000:
                        st.info(f"Showing first 2000 characters. Full text has {len(text_data['full_text'])} characters.")

                progress_bar.progress(35)

                # Step 4: Run DataField Agent
                status_text.text("🤖 Running DataField Agent (Step 1/3)...")

                # Check if API key exists
                api_config_path = kg_dir / "api.json"
                if not api_config_path.exists():
                    st.error("❌ api.json not found. Cannot run AI agents.")
                    st.info("Please create api.json with Gemini API key to use AI agents.")
                    return

                # Use process_policy.py to run all 3 agents
                initial_data_dict = kg_dir / "test1" / "Data_dictionary.json"
                datafield_prompt = kg_dir / "prompts" / "DataField" / "1.txt"
                policy_prompt = kg_dir / "prompts" / "Policy" / "1.txt"
                sql_prompt = kg_dir / "prompts" / "SQL" / "1.txt"

                # Check if required files exist
                required_files = [initial_data_dict, datafield_prompt, policy_prompt, sql_prompt]
                missing_files = [f for f in required_files if not f.exists()]

                if missing_files:
                    st.error(f"❌ Missing required files: {', '.join([f.name for f in missing_files])}")
                    return

                # Import and run process_policy
                sys.path.insert(0, str(kg_dir))
                try:
                    from process_policy import extract_data_fields, extract_policy_conditions, convert_to_sql
                except ImportError as e:
                    st.error(f"Failed to import process_policy: {e}")
                    return

                # Load initial data dictionary
                with open(initial_data_dict, 'r', encoding='utf-8') as f:
                    existing_dictionary = json.load(f)

                # Load policy text
                with open(txt_path, 'r', encoding='utf-8') as f:
                    policy_text = f.read()

                # Step 4: Extract data fields
                progress_bar.progress(45)

                try:
                    data_fields = extract_data_fields(policy_text, existing_dictionary, str(datafield_prompt))
                    data_dict_path = policy_dir / f"Data_dictionary_{policy_id}.json"
                    with open(data_dict_path, 'w', encoding='utf-8') as f:
                        json.dump(data_fields, f, indent=2)
                    st.success(f"✅ Step 1 - DataField Agent complete: {data_dict_path}")
                except Exception as e:
                    st.error(f"❌ DataField Agent failed: {e}")
                    return

                progress_bar.progress(60)

                # Step 5: Extract policy conditions
                status_text.text("🤖 Running Policy Agent (Step 2/3)...")

                try:
                    policies = extract_policy_conditions(policy_text, data_fields, str(policy_prompt))
                    policy_json_path = policy_dir / f"Policy_{policy_id}.json"
                    with open(policy_json_path, 'w', encoding='utf-8') as f:
                        json.dump(policies, f, indent=2)
                    st.success(f"✅ Step 2 - Policy Agent complete: {policy_json_path}")
                except Exception as e:
                    st.error(f"❌ Policy Agent failed: {e}")
                    return

                progress_bar.progress(75)

                # Step 6: Convert to SQL
                status_text.text("🤖 Running SQL Agent (Step 3/3)...")

                try:
                    sql_queries = []
                    for policy in policies:
                        sql = convert_to_sql(policy, str(sql_prompt))
                        sql_queries.append(sql)

                    sql_path = policy_dir / f"SQL_{policy_id}.txt"
                    with open(sql_path, 'w', encoding='utf-8') as f:
                        f.write('\n\n---\n\n'.join(sql_queries))
                    st.success(f"✅ Step 3 - SQL Agent complete: {sql_path}")
                except Exception as e:
                    st.error(f"❌ SQL Agent failed: {e}")
                    return

                progress_bar.progress(85)

                # Step 7: Generate Policy Knowledge Graph (Interactive)
                status_text.text("🎨 Generating Policy Knowledge Graph...")

                plot_path = None
                png_path = None

                try:
                    # Use interactive generator for better visualization
                    generator = PolicyRuleKGGenerator_WithInteractive(
                        sql_path=str(sql_path),
                        data_dictionary_path=str(data_dict_path),
                        policy_id=policy_id,
                        output_dir=str(policy_dir)
                    )

                    nodes, edges = generator.generate()

                    # Save JSON files
                    nodes_path, edges_path = generator.save_json()

                    # Try to generate interactive HTML plot
                    try:
                        plot_path = policy_dir / f"policy_rule_kg_interactive_{policy_id}.html"
                        html_result = generator.plot_interactive(output_path=str(plot_path))
                        if html_result:
                            st.success(f"✅ Interactive HTML generated")
                        else:
                            st.warning("⚠️ Interactive HTML generation skipped")
                            plot_path = None
                    except Exception as e:
                        st.warning(f"⚠️ Interactive HTML failed: {e}")
                        plot_path = None

                    # Always generate static PNG version as fallback
                    try:
                        png_path = policy_dir / f"policy_rule_kg_{policy_id}.png"
                        png_result = generator.plot(output_path=str(png_path), show=False)
                        if png_result:
                            st.success(f"✅ Static PNG generated")
                        else:
                            st.warning("⚠️ Static PNG generation skipped")
                            png_path = None
                    except Exception as e:
                        st.warning(f"⚠️ Static PNG failed: {e}")
                        png_path = None

                    # Check if at least one was successful
                    if plot_path or png_path:
                        st.success(f"✅ Policy KG generated successfully")
                    else:
                        st.warning("⚠️ Could not generate any visualization")

                except Exception as e:
                    st.error(f"❌ Policy KG generation failed: {e}")
                    import traceback
                    st.error(traceback.format_exc())

                progress_bar.progress(100)
                status_text.text("✅ Policy conversion complete!")

                # Initialize png_path if not already set
                if 'png_path' not in locals():
                    png_path = None

                # Display results
                st.markdown('<h2 class="section-header">📊 Conversion Results</h2>', unsafe_allow_html=True)

                # Show generated files in expander
                with st.expander("📁 Generated Files", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Files:**")
                        policy_files = list(policy_dir.glob("*"))
                        for file_path in sorted(policy_files):
                            file_size = file_path.stat().st_size
                            st.write(f"- {file_path.name} ({file_size:,} bytes)")

                    with col2:
                        st.markdown("**Data Dictionary Fields:**")
                        if data_dict_path.exists():
                            with open(data_dict_path, 'r', encoding='utf-8') as f:
                                data_dict = json.load(f)
                            st.write(f"Total fields: {len(data_dict)}")

                # Display Policy KG
                st.markdown('<h2 class="section-header">🎨 Policy Knowledge Graph</h2>', unsafe_allow_html=True)

                # Display interactive HTML as main visualization
                st.markdown("### 🖱️ Interactive Graph (Zoomable & Draggable)")

                # Try to find interactive HTML file (more robust)
                interactive_html_candidates = list(policy_dir.glob("*_interactive.html"))
                if interactive_html_candidates:
                    interactive_html_path = interactive_html_candidates[0]
                    with open(interactive_html_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=800, scrolling=True)

                    # Download button for HTML
                    with open(interactive_html_path, "rb") as file:
                        st.download_button(
                            label="📥 Download Interactive HTML",
                            data=file.read(),
                            file_name=interactive_html_path.name,
                            mime="text/html"
                        )
                elif plot_path and plot_path.exists():
                    # Fallback to plot_path variable
                    with open(plot_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=800, scrolling=True)

                    # Download button for HTML
                    with open(plot_path, "rb") as file:
                        st.download_button(
                            label="📥 Download Interactive HTML",
                            data=file.read(),
                            file_name=plot_path.name,
                            mime="text/html"
                        )
                else:
                    st.warning("⚠️ Interactive HTML not generated.")

                # Show PNG as backup/alternative
                with st.expander("📸 View Static Image (Backup)", expanded=False):
                    if png_path and png_path.exists():
                        st.image(str(png_path), use_container_width=True)

                        # Download button for PNG
                        with open(png_path, "rb") as file:
                            st.download_button(
                                label="📥 Download PNG",
                                data=file.read(),
                                file_name=png_path.name,
                                mime="image/png"
                            )
                    else:
                        st.info("Static PNG not generated.")

                # Show extracted data
                with st.expander("📋 View Data Dictionary", expanded=False):
                    if data_dict_path.exists():
                        with open(data_dict_path, 'r', encoding='utf-8') as f:
                            st.json(json.load(f))

                with st.expander("📜 View Policy JSON", expanded=False):
                    if policy_json_path.exists():
                        with open(policy_json_path, 'r', encoding='utf-8') as f:
                            st.json(json.load(f))

                with st.expander("💾 View SQL Query", expanded=False):
                    if sql_path.exists():
                        with open(sql_path, 'r', encoding='utf-8') as f:
                            st.code(f.read(), language='sql')

                st.success(f"🎉 All files saved to: {policy_dir}")

            except Exception as e:
                st.error(f"❌ Error during policy conversion: {e}")
                import traceback
                st.error(traceback.format_exc())
                progress_bar.progress(0)
                status_text.text("❌ Conversion failed")

    else:
        # Instructions
        st.markdown("""
        <div class="info-box">
        <h3>📋 How to use Policy Conversion:</h3>
        <ol>
            <li><strong>Upload Policy PDF:</strong> Select a medical policy PDF file</li>
            <li><strong>Click Convert:</strong> The system will automatically:
                <ul>
                    <li>Extract text using OCR</li>
                    <li>Run DataField Agent to identify data fields</li>
                    <li>Run Policy Agent to extract policy conditions</li>
                    <li>Run SQL Agent to generate SQL queries</li>
                    <li>Generate Policy Knowledge Graph</li>
                </ul>
            </li>
            <li><strong>View Results:</strong> Examine the generated files and visualizations</li>
            <li><strong>Download:</strong> All files are organized in <code>Run_Time_Policy/{policy_id}/</code></li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

def sql_queries_page():
    """SQL Queries and Database Management Page."""

    # Header
    st.markdown('<h1 class="main-header">🗄️ SQL Queries & Database Management</h1>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("📊 Database Options")

    # Check if database exists
    db_path = get_database_path()
    if not os.path.exists(db_path):
        st.error(f"❌ Database not found: {db_path}")
        st.info("Please ensure the database exists before using SQL queries.")
        return

    st.success(f"✅ Database found: {db_path}")

    # Main content
    st.markdown('<h2 class="section-header">📋 Available Operations</h2>', unsafe_allow_html=True)

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📊 View All Data", "🔍 Run Policy Filters", "🗑️ Delete Patient"])

    with tab1:
        st.markdown('<h3 class="section-header">View All Patient Data</h3>', unsafe_allow_html=True)
        st.write("Display all patient records in the database. Duplicates are automatically removed before displaying data.")

        if st.button("📊 Load All Patient Data (Auto-Remove Duplicates)", type="primary"):
            with st.spinner("Loading patient data and removing duplicates..."):
                df = get_all_patients()

                if df is not None and not df.empty:
                    st.success(f"✅ Loaded {len(df)} patient records (duplicates automatically removed)")

                    # Display basic statistics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Patients", len(df))
                    with col2:
                        st.metric("Database Size", f"{os.path.getsize(db_path):,} bytes")

                    # Display the data
                    st.markdown('<h4 class="section-header">Patient Data Table</h4>', unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)

                    # Download options
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name="patient_data.csv",
                            mime="text/csv"
                        )
                    with col2:
                        json_data = df.to_json(orient='records', indent=2)
                        st.download_button(
                            label="📥 Download as JSON",
                            data=json_data,
                            file_name="patient_data.json",
                            mime="application/json"
                        )
                else:
                    st.warning("No patient data found in the database.")

    with tab2:
        st.markdown('<h3 class="section-header">Run Policy SQL Filters</h3>', unsafe_allow_html=True)
        st.write("Execute the policy SQL filter to find patients who meet the bariatric surgery criteria.")

        # Show the SQL query
        sql_path = kg_dir / "test1" / "Policy_CGSURG83" / "SQL_CGSURG83.txt"
        if os.path.exists(sql_path):
            with st.expander("📄 View SQL Query", expanded=False):
                with open(sql_path, 'r', encoding='utf-8') as f:
                    sql_query = f.read()
                st.code(sql_query, language='sql')

        if st.button("🔍 Run Policy Filter", type="primary"):
            with st.spinner("Running policy SQL filter..."):
                df = run_policy_sql_filter()

                if df is not None and not df.empty:
                    st.success(f"✅ Found {len(df)} patients meeting policy criteria")

                    # Display basic statistics
                    st.metric("Eligible Patients", len(df))

                    # Display the filtered data
                    st.markdown('<h4 class="section-header">Eligible Patients</h4>', unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)

                    # Download options
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name="eligible_patients.csv",
                            mime="text/csv"
                        )
                    with col2:
                        json_data = df.to_json(orient='records', indent=2)
                        st.download_button(
                            label="📥 Download as JSON",
                            data=json_data,
                            file_name="eligible_patients.json",
                            mime="application/json"
                        )
                else:
                    st.warning("No patients found meeting the policy criteria.")

    with tab3:
        st.markdown('<h3 class="section-header">Delete Specific Patient</h3>', unsafe_allow_html=True)
        st.write("Delete a specific patient record from the database. You can either type the patient ID or select from the table below.")

        # Load and display current patients
        with st.spinner("Loading current patients..."):
            df = get_all_patients()

            if df is not None and not df.empty:
                st.success(f"Found {len(df)} patients in database")

                # Display the patient table
                st.markdown('<h4 class="section-header">Current Patients</h4>', unsafe_allow_html=True)
                st.dataframe(df, use_container_width=True)

                # Get patient IDs for selection
                patient_ids = df['patient_id'].tolist() if 'patient_id' in df.columns else []

                if patient_ids:
                    st.markdown("---")
                    st.markdown("**Select Patient to Delete:**")

                    # Single dropdown selection
                    patient_id_to_delete = st.selectbox(
                        "Choose Patient ID:",
                        options=[""] + patient_ids,
                        help="Select a patient ID from the dropdown"
                    )

                    if patient_id_to_delete:
                        # Show patient details before deletion
                        patient_data = df[df['patient_id'] == patient_id_to_delete]

                        if not patient_data.empty:
                            st.markdown("---")
                            st.markdown("**Patient Details to be Deleted:**")
                            st.dataframe(patient_data, use_container_width=True)

                            # Show confirmation
                            st.warning(f"⚠️ You are about to delete patient: **{patient_id_to_delete}**")
                            st.write("This action cannot be undone!")

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🗑️ Confirm Delete", type="primary"):
                                    with st.spinner("Deleting patient..."):
                                        if delete_patient_by_id(patient_id_to_delete):
                                            st.success(f"✅ Patient {patient_id_to_delete} deleted successfully!")
                                            st.rerun()  # Refresh the page
                                        else:
                                            st.error(f"❌ Failed to delete patient {patient_id_to_delete}")

                            with col2:
                                if st.button("❌ Cancel", type="secondary"):
                                    st.info("Deletion cancelled")
                        else:
                            st.error(f"Patient ID '{patient_id_to_delete}' not found in the current data")
                else:
                    st.warning("No patient IDs found in the data")
            else:
                st.warning("No patients found in the database")

    # Database info section
    st.markdown('<h2 class="section-header">ℹ️ Database Information</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Database Path:** `{db_path}`")
        st.info(f"**Database Size:** {os.path.getsize(db_path):,} bytes")

    with col2:
        st.info(f"**SQL File:** `{sql_path}`")
        if os.path.exists(sql_path):
            st.success("✅ SQL file found")
        else:
            st.error("❌ SQL file not found")

def policy_gallery_page():
    """Display available policies with interactive KG visualization."""
    st.markdown('<h1 class="main-header">📚 Policy Gallery</h1>', unsafe_allow_html=True)
    st.markdown("Browse and view all available policies with their knowledge graphs.")
    st.markdown("---")

    # Get all policies from Run_Time_Policy directory
    policies_dir = kg_dir / "Run_Time_Policy"

    if not policies_dir.exists():
        st.error("❌ Run_Time_Policy directory not found")
        return

    # Get all policy folders
    policy_folders = [d for d in policies_dir.iterdir() if d.is_dir()]

    if not policy_folders:
        st.info("ℹ️ No policies found. Create one using the Policy Conversion page.")
        return

    st.markdown(f"**Found {len(policy_folders)} policy(ies):**")

    # Create a list of policy names for selection
    policy_names = sorted([d.name for d in policy_folders])
    selected_policy = st.selectbox(
        "Select a policy to view:",
        policy_names,
        key="policy_gallery_selector"
    )

    if selected_policy:
        policy_dir = policies_dir / selected_policy
        st.markdown(f"## 📋 {selected_policy}")
        st.markdown("---")

        # Check for required files
        interactive_html = policy_dir / f"policy_rule_kg_interactive_{selected_policy}.html"
        static_png = policy_dir / f"policy_rule_kg_{selected_policy}.png"
        nodes_json = policy_dir / "policy_rule_kg_nodes.json"
        edges_json = policy_dir / "policy_rule_kg_edges.json"
        data_dict_json = policy_dir / f"Data_dictionary_{selected_policy}.json"
        policy_json = policy_dir / f"Policy_{selected_policy}.json"

        # Display policy info
        col1, col2, col3 = st.columns(3)
        with col1:
            # Count nodes
            if nodes_json.exists():
                with open(nodes_json, 'r', encoding='utf-8') as f:
                    nodes = json.load(f)
                st.metric("📌 Nodes", len(nodes))

        with col2:
            # Count edges
            if edges_json.exists():
                with open(edges_json, 'r', encoding='utf-8') as f:
                    edges = json.load(f)
                st.metric("🔗 Edges", len(edges))

        with col3:
            # Count fields
            if data_dict_json.exists():
                with open(data_dict_json, 'r', encoding='utf-8') as f:
                    data_dict = json.load(f)
                st.metric("📊 Fields", len(data_dict))

        st.markdown("### 🖱️ Interactive Graph (Zoomable & Draggable)")

        # Display interactive HTML
        if interactive_html.exists():
            with open(interactive_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=800, scrolling=True)

            # Download button for HTML
            with open(interactive_html, "rb") as file:
                st.download_button(
                    label="📥 Download Interactive HTML",
                    data=file.read(),
                    file_name=interactive_html.name,
                    mime="text/html",
                    key=f"download_html_{selected_policy}"
                )
        else:
            st.warning("⚠️ Interactive HTML not found")

        # Show PNG as backup/alternative
        with st.expander("📸 View Static Image (Backup)", expanded=False):
            if static_png.exists():
                st.image(str(static_png), use_container_width=True)

                # Download button for PNG
                with open(static_png, "rb") as file:
                    st.download_button(
                        label="📥 Download PNG",
                        data=file.read(),
                        file_name=static_png.name,
                        mime="image/png",
                        key=f"download_png_{selected_policy}"
                    )
            else:
                st.info("Static PNG not generated.")

        # Show node selector to view details
        st.markdown("### 📌 Node Information")
        nodes_for_sidebar = []
        if nodes_json.exists():
            with open(nodes_json, 'r', encoding='utf-8') as f:
                nodes_for_sidebar = json.load(f)

        if nodes_for_sidebar:
            # Create list of node labels for selection
            node_options = []
            node_map = {}

            for node in nodes_for_sidebar:
                node_id = node.get('id', '')
                label = node.get('label', node_id)
                node_options.append(f"{label} ({node_id})")
                node_map[f"{label} ({node_id})"] = node

            # Select node
            selected_option = st.selectbox(
                "Select a node to view details:",
                options=node_options,
                key=f"node_selector_{selected_policy}"
            )

            if selected_option:
                selected_node = node_map[selected_option]

                # Display node details in columns
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Basic Information:**")
                    st.markdown(f"**ID:** `{selected_node.get('id', 'N/A')}`")
                    st.markdown(f"**Type:** `{selected_node.get('type', 'N/A')}`")

                    if selected_node.get('label'):
                        st.markdown(f"**Label:** {selected_node.get('label')}")

                    if selected_node.get('section'):
                        st.markdown(f"**Section:** `{selected_node.get('section')}`")

                with col2:
                    st.markdown("**Condition Details:**")
                    if selected_node.get('field_name'):
                        st.markdown(f"**Field Name:** `{selected_node.get('field_name')}`")

                    if selected_node.get('operator'):
                        st.markdown(f"**Operator:** `{selected_node.get('operator')}`")

                    if selected_node.get('value'):
                        st.markdown(f"**Value:** `{selected_node.get('value')}`")

                    if selected_node.get('condition_type'):
                        st.markdown(f"**Condition Type:** `{selected_node.get('condition_type')}`")

                if selected_node.get('description'):
                    st.markdown("**Description:**")
                    st.markdown(selected_node.get('description'))

        # Show extracted data in expanders
        st.markdown("### 📁 Files & Data")

        with st.expander("📋 View Data Dictionary", expanded=False):
            if data_dict_json.exists():
                with open(data_dict_json, 'r', encoding='utf-8') as f:
                    st.json(json.load(f))
            else:
                st.info("Data dictionary not found.")

        with st.expander("📜 View Policy JSON", expanded=False):
            if policy_json.exists():
                with open(policy_json, 'r', encoding='utf-8') as f:
                    st.json(json.load(f))
            else:
                st.info("Policy JSON not found.")

        with st.expander("💾 View SQL Query", expanded=False):
            sql_txt = policy_dir / f"SQL_{selected_policy}.txt"
            if sql_txt.exists():
                with open(sql_txt, 'r', encoding='utf-8') as f:
                    st.code(f.read(), language='sql')
            else:
                st.info("SQL query not found.")

def main():
    """Main Streamlit application with page navigation."""

    # Page selection in sidebar
    st.sidebar.title("🏥 Medical KG App")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["📚 Policy Gallery", "📄 Medical Records", "📋 Policy Conversion", "🗄️ SQL Queries"]
    )

    # Route to appropriate page
    if page == "📚 Policy Gallery":
        policy_gallery_page()
    elif page == "📄 Medical Records":
        medical_record_page()
    elif page == "📋 Policy Conversion":
        policy_conversion_page()
    elif page == "🗄️ SQL Queries":
        sql_queries_page()

if __name__ == "__main__":
    main()
