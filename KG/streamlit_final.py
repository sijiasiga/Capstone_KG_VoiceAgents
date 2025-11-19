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
import sys
import re
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
    from patient_rule_kg_interactive import PatientRuleKGVisualizer as PatientRuleKGVisualizerInteractive
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

def generate_patient_kg(patient_data: Dict[str, Any], patient_dir: str, show_plot: bool = True, show_text: bool = True, force_regenerate: bool = False) -> Optional[str]:
    """Generate patient knowledge graph (interactive HTML).

    Args:
        patient_data: Patient data dictionary
        patient_dir: Directory to save the plot
        show_plot: Whether to show the plot (default: True)
        show_text: Whether to show text labels on nodes (default: True)
        force_regenerate: Force regeneration even if file exists (default: False)

    Returns:
        Path to the generated HTML file
    """
    try:
        patient_dir_path = Path(patient_dir)

        # Determine filename based on show_text setting
        html_filename = "patient_kg_text_interactive.html" if show_text else "patient_kg_interactive.html"
        png_filename = "patient_kg_text_interactive.png" if show_text else "patient_kg_interactive.png"

        html_path = patient_dir_path / html_filename
        png_path = patient_dir_path / png_filename

        # Check if HTML file already exists
        if not force_regenerate and html_path.exists():
            st.info(f"ℹ️ Using existing Patient KG: {html_filename}")
            return str(html_path)

        # Load patient data from JSON file if available (for consistency)
        json_file = None
        for json_candidate in patient_dir_path.glob("Patient_data_*.json"):
            # Prefer the one matching the patient ID
            if patient_data.get('patient_id'):
                patient_id_clean = re.sub(r'[^a-zA-Z0-9]', '', str(patient_data.get('patient_id')))
                if patient_id_clean in json_candidate.name:
                    json_file = json_candidate
                    break
            else:
                json_file = json_candidate
                break

        if json_file and json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    loaded_patient_data = json.load(f)
                patient_data = loaded_patient_data
                st.info(f"ℹ️ Loaded patient data from: {json_file.name}")
            except Exception as json_error:
                st.warning(f"⚠️ Could not load patient data from JSON: {json_error}")

        # Create visualizer
        visualizer = PatientKGVisualizer(patient_data)
        visualizer.build_graph()

        # Generate interactive plot as HTML
        plot_path_prefix = str(html_path.with_suffix(''))  # Remove .html suffix for the function
        result_path = visualizer.create_plotly_visualization(
            layout='spring',
            output_file=plot_path_prefix,
            input_file_path=None,
            show_text=show_text
        )

        # PNG backup generation is optional (requires kaleido package)
        # Skipping for now as HTML visualization is the primary format

        return result_path
    except Exception as e:
        st.error(f"Error generating patient KG: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def generate_patient_rule_kg(patient_data: Dict[str, Any], patient_dir: str, show_plot: bool = True, policy_id: str = None, policy_sql: str = None, policy_json: Dict = None, show_text: bool = True, force_regenerate: bool = False) -> Optional[str]:
    """Generate interactive patient rule knowledge graph using specified policy.

    Args:
        patient_data: Patient data dictionary
        patient_dir: Directory to save the plot
        show_plot: Whether to show the plot (default: True)
        policy_id: Policy identifier
        policy_sql: SQL rules
        policy_json: Policy JSON data
        show_text: Whether to show text labels on nodes (default: True)
        force_regenerate: Force regeneration even if file exists (default: False)

    Returns:
        Path to the generated HTML file
    """
    try:
        patient_dir_path = Path(patient_dir)

        # Load patient data from JSON file if available (for consistency)
        json_file = None
        for json_candidate in patient_dir_path.glob("Patient_data_*.json"):
            # Prefer the one matching the patient ID
            if patient_data.get('patient_id'):
                patient_id_clean = re.sub(r'[^a-zA-Z0-9]', '', str(patient_data.get('patient_id')))
                if patient_id_clean in json_candidate.name:
                    json_file = json_candidate
                    break
            else:
                json_file = json_candidate
                break

        if json_file and json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    loaded_patient_data = json.load(f)
                patient_data = loaded_patient_data
                st.info(f"ℹ️ Loaded patient data from: {json_file.name}")
            except Exception as json_error:
                st.warning(f"⚠️ Could not load patient data from JSON: {json_error}")

        # If policy info is provided, use it; otherwise fall back to CGSURG83
        if policy_sql and policy_json:
            sql_text = policy_sql
            policy_data = policy_json
            policy_name = policy_id or "custom_policy"
        else:
            # Fallback to CGSURG83
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

            policy_name = "CGSURG83"

        # Determine filename based on show_text setting
        html_filename = f"patient_rule_kg_{policy_name}_text.html" if show_text else f"patient_rule_kg_{policy_name}.html"
        png_filename = f"patient_rule_kg_{policy_name}_text.png" if show_text else f"patient_rule_kg_{policy_name}.png"

        html_path = patient_dir_path / html_filename
        png_path = patient_dir_path / png_filename

        # Check if HTML file already exists
        if not force_regenerate and html_path.exists():
            st.info(f"ℹ️ Using existing Compliance KG: {html_filename}")
            return str(html_path)

        # Create interactive visualizer
        visualizer = PatientRuleKGVisualizerInteractive(patient_data, sql_text, policy_data)
        visualizer.parse_and_evaluate_conditions()
        visualizer.apply_logical_operators()
        visualizer.build_knowledge_graph()

        # Generate interactive plot as HTML
        saved_path = visualizer.plot_interactive(output_path=str(html_path), show_text=show_text)

        # PNG backup generation is optional (requires kaleido package)
        # Skipping for now as HTML visualization is the primary format

        # Generate compliance report
        patient_id = patient_data.get('patient_id', 'unknown')
        compliance_path = visualizer.generate_compliance_report(
            patient_id, policy_name, patient_dir
        )

        return str(saved_path) if saved_path else str(html_path)
    except Exception as e:
        st.error(f"Error generating patient rule KG: {e}")
        return None

def run_patient_record_ocr(pdf_path: str, patient_dir: str) -> str:
    """Run patient record OCR to extract text using patient_record_ocr module."""
    txt_path = Path(patient_dir) / f"{Path(pdf_path).stem}.txt"

    try:
        # Import patient record OCR module
        sys.path.insert(0, str(kg_dir / "OCR"))
        from patient_record_ocr import PatientRecordOCRCleaner
        import fitz  # PyMuPDF

        # Extract text using patient record OCR
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        # Clean the text
        cleaner = PatientRecordOCRCleaner()
        cleaned_text = cleaner.clean_text(full_text)

        # Save the cleaned text
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)

        return str(txt_path)
    except Exception as e:
        st.error(f"Error in patient record OCR: {e}")
        return None

def process_patient_record_data(txt_path: str, patient_dir: str, data_dictionary: Dict[str, Any], prompt_path: str) -> Optional[Dict[str, Any]]:
    """Process patient record text to extract structured data using process_patient_record module."""
    try:
        # Read the text file
        with open(txt_path, 'r', encoding='utf-8') as f:
            record_text = f.read()

        # Load the prompt
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()

        # Import process_patient_record module
        sys.path.insert(0, str(kg_dir))
        from process_patient_record import extract_patient_record

        # Extract patient record using Gemini API
        extracted_data = extract_patient_record(record_text, data_dictionary, prompt)

        # Handle if the API returns a list instead of dict (extract first element if it's a list)
        if isinstance(extracted_data, list):
            if len(extracted_data) > 0:
                patient_data = extracted_data[0] if isinstance(extracted_data[0], dict) else extracted_data
            else:
                st.error("Empty response from patient record extraction")
                return None
        elif isinstance(extracted_data, dict):
            patient_data = extracted_data
        else:
            st.error(f"Unexpected data type from extraction: {type(extracted_data)}")
            return None

        # Ensure patient_data is a dictionary
        if not isinstance(patient_data, dict):
            st.error("Failed to extract patient data as dictionary")
            return None

        # Save the extracted data
        patient_id = patient_data.get('patient_id', 'unknown')
        patient_dir_path = Path(patient_dir).resolve()  # Ensure absolute path
        json_path = patient_dir_path / f"Patient_data_{patient_id}.json"

        with open(str(json_path), 'w', encoding='utf-8') as f:
            json.dump(patient_data, f, indent=2)

        return patient_data
    except Exception as e:
        st.error(f"Error processing patient record: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def get_available_policies() -> Dict[str, Path]:
    """Get all available policies from Run_Time_Policy directory."""
    policies_dir = kg_dir / "Run_Time_Policy"
    policies = {}

    if policies_dir.exists():
        for policy_folder in policies_dir.iterdir():
            if policy_folder.is_dir():
                policies[policy_folder.name] = policy_folder

    return policies

def load_policy_data(policy_dir: Path, policy_id: str) -> Optional[Dict[str, Any]]:
    """Load policy data (SQL, conditions, data dictionary) from a policy folder."""
    try:
        policy_data = {
            "policy_id": policy_id,
            "sql_path": None,
            "sql_content": None,
            "policy_json": None,
            "data_dictionary": None
        }

        # Load SQL file
        sql_file = policy_dir / f"SQL_{policy_id}.txt"
        if sql_file.exists():
            with open(sql_file, 'r', encoding='utf-8') as f:
                policy_data["sql_content"] = f.read()
                policy_data["sql_path"] = str(sql_file)

        # Load policy JSON
        policy_json_file = policy_dir / f"Policy_{policy_id}.json"
        if policy_json_file.exists():
            with open(policy_json_file, 'r', encoding='utf-8') as f:
                policy_data["policy_json"] = json.load(f)

        # Load data dictionary
        data_dict_file = policy_dir / f"Data_dictionary_{policy_id}.json"
        if data_dict_file.exists():
            with open(data_dict_file, 'r', encoding='utf-8') as f:
                policy_data["data_dictionary"] = json.load(f)

        return policy_data
    except Exception as e:
        st.error(f"Error loading policy data: {e}")
        return None

def patient_compliance_page():
    """Patient Compliance Assessment Page - Process patient records and check policy compliance."""

    # Header
    st.markdown('<h1 class="main-header">👤 Patient Compliance Assessment</h1>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <h4>📋 About Patient Compliance</h4>
    <p>This tool processes patient records and evaluates their compliance against selected medical policies:</p>
    <ul>
        <li><strong>Patient Record OCR:</strong> Extracts and cleans text from patient record PDFs</li>
        <li><strong>Data Extraction:</strong> Extracts structured data from patient records using AI</li>
        <li><strong>Policy Selection:</strong> Choose which policy to evaluate compliance against</li>
        <li><strong>Compliance Analysis:</strong> Generate compliance assessment and visualizations</li>
    </ul>
    <p>All patient data is organized in <code>Run_Time_Patient/Patient_{patient_id}/</code></p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("📋 Compliance Options")

    # Step 1: Policy Selection
    st.markdown('<h2 class="section-header">1️⃣ Select Policy</h2>', unsafe_allow_html=True)

    available_policies = get_available_policies()

    if not available_policies:
        st.error("❌ No policies found in Run_Time_Policy directory")
        st.info("Please create at least one policy using the Policy Conversion page first.")
        return

    policy_names = sorted(list(available_policies.keys()))
    selected_policy = st.selectbox(
        "Choose a policy to evaluate against:",
        policy_names,
        key="patient_compliance_policy_selector"
    )

    if selected_policy:
        policy_dir = available_policies[selected_policy]
        policy_data = load_policy_data(policy_dir, selected_policy)

        if policy_data:
            st.success(f"✅ Policy selected: {selected_policy}")

            # Display policy info
            col1, col2, col3 = st.columns(3)
            with col1:
                if policy_data["data_dictionary"]:
                    st.metric("📊 Fields", len(policy_data["data_dictionary"]))
            with col2:
                if policy_data["policy_json"]:
                    st.metric("📋 Rules", len(policy_data["policy_json"]))
            with col3:
                st.metric("✅ Ready", "Yes")

            # Step 2: Patient Record Upload
            st.markdown('<h2 class="section-header">2️⃣ Upload Patient Record</h2>', unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Choose a patient record PDF file",
                type="pdf",
                help="Upload a patient record PDF to process",
                key="patient_compliance_upload"
            )

            if uploaded_file is not None:
                # Display file info
                st.success(f"✅ File uploaded: {uploaded_file.name}")
                st.info(f"📊 File size: {uploaded_file.size:,} bytes")

                # Step 3: Processing Options
                st.markdown('<h2 class="section-header">3️⃣ Processing Configuration</h2>', unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)

                with col1:
                    auto_process = st.checkbox("Auto Process", value=True, help="Automatically process after upload")
                    show_patient_kg = st.checkbox("Show Patient KG", value=True, help="Display patient knowledge graph")

                with col2:
                    show_compliance_kg = st.checkbox("Show Compliance KG", value=True, help="Display compliance assessment graph")

                # Check if this file has already been processed (to prevent re-processing on checkbox changes)
                current_file_id = f"{uploaded_file.name}_{uploaded_file.size}_{selected_policy}"
                file_already_processed = (
                    hasattr(st.session_state, 'last_processed_file_id') and
                    st.session_state.last_processed_file_id == current_file_id
                )

                # Process button
                should_process = (st.button("🚀 Process Patient Record", type="primary") or auto_process) and not file_already_processed

                if should_process:

                    # Create progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        # Step 1: Create Run_Time_Patient folder structure
                        status_text.text("📁 Setting up patient folder...")
                        progress_bar.progress(5)

                        runtime_patient_dir = kg_dir / "Run_Time_Patient"
                        runtime_patient_dir.mkdir(exist_ok=True)

                        # Extract patient ID from filename (or use a placeholder if not found)
                        patient_id_candidate = Path(uploaded_file.name).stem
                        # For now, we'll use the filename stem as patient ID
                        patient_id = patient_id_candidate if patient_id_candidate and patient_id_candidate != "MR_2" else "patient_temp"

                        # Create patient-specific folder
                        patient_dir = runtime_patient_dir / f"Patient_{patient_id}"
                        patient_dir.mkdir(exist_ok=True)

                        st.success(f"✅ Patient folder created: {patient_dir}")

                        # Step 2: Save uploaded file
                        status_text.text("💾 Saving patient record PDF...")
                        progress_bar.progress(10)

                        pdf_path = patient_dir / uploaded_file.name
                        with open(pdf_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        st.success(f"✅ PDF saved: {pdf_path}")

                        # Step 3: Run patient record OCR
                        status_text.text("🔍 Running patient record OCR...")
                        progress_bar.progress(25)

                        txt_path = run_patient_record_ocr(str(pdf_path), str(patient_dir))
                        if txt_path:
                            st.success(f"✅ OCR complete: {txt_path}")
                        else:
                            st.error("❌ Failed to extract text from patient record")
                            return

                        # Display extracted text preview
                        with st.expander("📄 View Extracted Text (Preview)", expanded=False):
                            with open(txt_path, 'r', encoding='utf-8') as f:
                                preview_text = f.read()[:2000]
                            st.text_area("Extracted Text", preview_text, height=200)

                        progress_bar.progress(40)

                        # Step 4: Process patient record data
                        status_text.text("🤖 Processing patient record data...")
                        progress_bar.progress(50)

                        # Check if patient data is already cached in session state (to prevent re-running Gemini on checkbox changes)
                        # Note: current_file_id is already defined at line 617 above
                        if (hasattr(st.session_state, 'patient_compliance_data') and
                            st.session_state.patient_compliance_data.get('selected_policy') == selected_policy and
                            st.session_state.patient_compliance_data.get('file_id') == current_file_id):
                            # Reuse cached data
                            patient_data = st.session_state.patient_compliance_data['patient_data']
                            patient_dir = Path(st.session_state.patient_compliance_data['patient_dir'])
                            st.info("ℹ️ Using cached patient data (no re-extraction needed)")
                            st.success("✅ Patient record processed successfully (cached)")
                        else:
                            # Check if we have a prompt file for patient record extraction
                            patient_prompt_path = kg_dir / "prompts" / "Patient_Record_Parser" / "0.txt"

                            if patient_prompt_path.exists() and policy_data["data_dictionary"]:
                                # Debug info
                                st.info(f"📋 Using data dictionary from policy: {selected_policy}")
                                st.info(f"📄 Using prompt: {patient_prompt_path.name}")

                                patient_data = process_patient_record_data(
                                    txt_path,
                                    str(patient_dir),
                                    policy_data["data_dictionary"],
                                    str(patient_prompt_path)
                                )

                            else:
                                patient_data = None

                            if patient_data:
                                st.success("✅ Patient record processed successfully")

                                # Update patient_id if extracted from data
                                extracted_patient_id = patient_data.get('patient_id', patient_id)
                                if extracted_patient_id and extracted_patient_id != patient_id:
                                    # Remove all special characters, keep alphanumeric only
                                    patient_id = re.sub(r'[^a-zA-Z0-9]', '', str(extracted_patient_id))
                                    # Rename folder if patient ID changed
                                    new_patient_dir = runtime_patient_dir / f"Patient_{patient_id}"

                                    # Move files from old directory to new directory
                                    if new_patient_dir != patient_dir:
                                        try:
                                            # Create new directory if it doesn't exist
                                            new_patient_dir.mkdir(exist_ok=True)

                                            # Move all files from old to new directory
                                            for item in patient_dir.iterdir():
                                                if item.is_file():
                                                    shutil.move(str(item), str(new_patient_dir / item.name))

                                            # Remove old empty directory
                                            if patient_dir != new_patient_dir and list(patient_dir.iterdir()) == []:
                                                patient_dir.rmdir()

                                            patient_dir = new_patient_dir
                                            st.success(f"✅ Patient folder renamed to: {patient_dir.name}")

                                            # Rename JSON file to match new patient_id
                                            old_json = list(patient_dir.parent.glob(f"Patient_data_*.json"))
                                            if old_json:
                                                old_json_path = old_json[0]
                                                new_json_path = patient_dir / f"Patient_data_{patient_id}.json"
                                                shutil.move(str(old_json_path), str(new_json_path))
                                                st.success(f"✅ Patient data file renamed")
                                        except Exception as e:
                                            st.warning(f"⚠️ Could not rename folder: {e}")
                                            # Continue with processing even if rename fails

                                # Display extracted data
                                with st.expander("📊 Extracted Patient Data", expanded=True):
                                    st.json(patient_data)
                            else:
                                st.error("❌ Failed to process patient record")
                                st.info("💡 Troubleshooting tips:")
                                st.write("- Check if the data dictionary format is correct")
                                st.write("- Check if the prompt file is appropriate for this data dictionary")
                                st.write("- Verify the patient record PDF contains relevant information")
                                return

                        progress_bar.progress(60)

                        # Store patient data in session state to prevent re-processing on checkbox changes
                        # Include file_id to ensure cache is only used for the SAME uploaded file
                        st.session_state.patient_compliance_data = {
                            'patient_dir': str(patient_dir),
                            'patient_data': patient_data,
                            'selected_policy': selected_policy,
                            'file_id': current_file_id
                        }
                        st.session_state.show_compliance_kg_options = True

                        # Step 5: Configure Regeneration Options
                        st.markdown('<h2 class="section-header">4️⃣ Regeneration Options</h2>', unsafe_allow_html=True)

                        force_regenerate = st.checkbox("Force Regenerate", value=False, help="Regenerate KGs even if files exist", key="force_regenerate_checkbox")

                        # Fixed text display settings
                        show_patient_kg_text = False  # Patient KG without text
                        show_compliance_kg_text = True  # Compliance KG with text

                        # Step 6: Generate Knowledge Graphs
                        # Check if KGs have already been generated for this patient (avoiding re-generation on checkbox toggle)
                        # Include patient_dir in the key to ensure KGs are only generated once per patient+policy combination
                        kg_generation_key = f"kg_generated_{patient_id}_{selected_policy}"

                        if kg_generation_key not in st.session_state or force_regenerate:
                            status_text.text("🎨 Generating knowledge graphs...")

                            # Patient KG - Generate BOTH text and no-text versions
                            if show_patient_kg and patient_data:
                                with st.spinner("Generating Patient KG (both versions)..."):
                                    # Generate text version
                                    generate_patient_kg(patient_data, str(patient_dir), show_plot=False, show_text=True, force_regenerate=force_regenerate)
                                    # Generate no-text version
                                    generate_patient_kg(patient_data, str(patient_dir), show_plot=False, show_text=False, force_regenerate=force_regenerate)
                                    st.success("✅ Patient KG generated (both versions)")
                                progress_bar.progress(80)

                            # Compliance KG - Generate BOTH text and no-text versions
                            if show_compliance_kg and patient_data and policy_data["policy_json"]:
                                with st.spinner("Generating Compliance Assessment (both versions)..."):
                                    # Generate text version
                                    generate_patient_rule_kg(
                                        patient_data,
                                        str(patient_dir),
                                        show_plot=False,
                                        policy_id=selected_policy,
                                        policy_sql=policy_data["sql_content"],
                                        policy_json=policy_data["policy_json"],
                                        show_text=True,
                                        force_regenerate=force_regenerate
                                    )
                                    # Generate no-text version
                                    generate_patient_rule_kg(
                                        patient_data,
                                        str(patient_dir),
                                        show_plot=False,
                                        policy_id=selected_policy,
                                        policy_sql=policy_data["sql_content"],
                                        policy_json=policy_data["policy_json"],
                                        show_text=False,
                                        force_regenerate=force_regenerate
                                    )
                                    st.success("✅ Compliance assessment generated (both versions)")
                                progress_bar.progress(90)

                            # Mark KGs as generated for this policy
                            st.session_state[kg_generation_key] = True
                        else:
                            st.info("✅ Using previously generated knowledge graphs")
                            progress_bar.progress(90)

                        # Step 7: Determine which plots to display based on checkbox state
                        generated_plots = {}

                        # Patient KG - select based on checkbox
                        if show_patient_kg and patient_data:
                            patient_kg_filename = "patient_kg_text_interactive.html" if show_patient_kg_text else "patient_kg_interactive.html"
                            patient_kg_path = Path(patient_dir) / patient_kg_filename
                            if patient_kg_path.exists():
                                generated_plots["Patient KG"] = str(patient_kg_path)

                        # Compliance KG - select based on checkbox
                        if show_compliance_kg and patient_data and policy_data["policy_json"]:
                            compliance_kg_filename = f"patient_rule_kg_{selected_policy}_text.html" if show_compliance_kg_text else f"patient_rule_kg_{selected_policy}.html"
                            compliance_kg_path = Path(patient_dir) / compliance_kg_filename
                            if compliance_kg_path.exists():
                                generated_plots["Compliance Assessment"] = str(compliance_kg_path)

                        progress_bar.progress(100)
                        status_text.text("✅ Processing complete!")

                        # Step 8: Display Results
                        st.markdown('<h2 class="section-header">📊 Results</h2>', unsafe_allow_html=True)

                        if generated_plots:
                            # Create tabs for different plots
                            tab_names = list(generated_plots.keys())
                            tabs = st.tabs(tab_names)

                            for i, (plot_name, plot_path) in enumerate(generated_plots.items()):
                                with tabs[i]:
                                    st.subheader(f"{plot_name}")

                                    if os.path.exists(plot_path):
                                        # Check if it's an HTML file (interactive) or image file (static)
                                        if plot_path.endswith('.html'):
                                            # Display interactive HTML plot
                                            with open(plot_path, 'r', encoding='utf-8') as f:
                                                html_content = f.read()
                                            st.components.v1.html(html_content, height=900, scrolling=True)

                                            # Download button for HTML
                                            with open(plot_path, "rb") as file:
                                                st.download_button(
                                                    label=f"📥 Download {plot_name} (HTML)",
                                                    data=file.read(),
                                                    file_name=os.path.basename(plot_path),
                                                    mime="text/html",
                                                    key=f"download_{plot_name}_{patient_id}"
                                                )
                                        else:
                                            # Display image plot
                                            st.image(plot_path, use_container_width=True)

                                            # Download button for image
                                            with open(plot_path, "rb") as file:
                                                st.download_button(
                                                    label=f"📥 Download {plot_name}",
                                                    data=file.read(),
                                                    file_name=os.path.basename(plot_path),
                                                    mime="image/png",
                                                    key=f"download_{plot_name}_{patient_id}"
                                                )
                                    else:
                                        st.error(f"Plot file not found: {plot_path}")

                        # Step 9: Display Policy Information
                        st.markdown('<h2 class="section-header">📋 Policy Information</h2>', unsafe_allow_html=True)

                        with st.expander("View SQL Query", expanded=False):
                            if policy_data["sql_content"]:
                                st.code(policy_data["sql_content"], language='sql')
                            else:
                                st.info("SQL query not available")

                        with st.expander("View Policy JSON", expanded=False):
                            if policy_data["policy_json"]:
                                st.json(policy_data["policy_json"])
                            else:
                                st.info("Policy JSON not available")

                        # Step 10: File Organization
                        st.markdown('<h2 class="section-header">📁 Generated Files</h2>', unsafe_allow_html=True)

                        if st.button("📂 Show Patient Files"):
                            st.info(f"Patient files are saved in: {patient_dir}")

                            # List files in patient directory
                            patient_files = list(patient_dir.glob("*"))
                            if patient_files:
                                st.write("**Files in patient folder:**")
                                for file_path in sorted(patient_files):
                                    file_size = file_path.stat().st_size
                                    st.write(f"- {file_path.name} ({file_size:,} bytes)")
                            else:
                                st.write("No files found in patient folder.")

                        # Mark this file as processed to prevent re-processing on checkbox changes
                        st.session_state.last_processed_file_id = current_file_id

                    except Exception as e:
                        st.error(f"❌ Error during processing: {e}")
                        import traceback
                        st.error(traceback.format_exc())
                        progress_bar.progress(0)
                        status_text.text("❌ Processing failed")

            else:
                # Instructions when no file is uploaded
                st.markdown("""
                <div class="info-box">
                <h3>📋 How to use this page:</h3>
                <ol>
                    <li><strong>Select Policy:</strong> Choose a policy to evaluate compliance against (from Policy Conversion)</li>
                    <li><strong>Upload Patient Record:</strong> Click the file uploader to select a patient record PDF</li>
                    <li><strong>Configure Options:</strong> Choose which visualizations to generate</li>
                    <li><strong>Process:</strong> Click "Process Patient Record" or enable "Auto Process"</li>
                    <li><strong>View Results:</strong> Examine compliance assessment and knowledge graphs</li>
                </ol>

                <h4>📁 Folder Structure:</h4>
                <p>All patient records are organized in: <code>Run_Time_Patient/Patient_{patient_id}/</code></p>
                <ul>
                    <li>Original patient record PDF</li>
                    <li>Extracted and cleaned text file</li>
                    <li>Structured patient data (JSON)</li>
                    <li>Patient knowledge graph visualizations</li>
                    <li>Compliance assessment visualizations</li>
                </ul>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load policy data")

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

                # Store in session state to prevent re-processing on checkbox changes
                st.session_state.patient_dir = str(patient_dir)
                st.session_state.patient_data = patient_data
                st.session_state.show_kg_options = True

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
                                # Check if it's an HTML file (interactive) or image file (static)
                                if plot_path.endswith('.html'):
                                    # Display interactive HTML plot
                                    with open(plot_path, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                    st.components.v1.html(html_content, height=900, scrolling=True)

                                    # Download button for HTML
                                    with open(plot_path, "rb") as file:
                                        st.download_button(
                                            label=f"📥 Download {plot_name} (HTML)",
                                            data=file.read(),
                                            file_name=os.path.basename(plot_path),
                                            mime="text/html",
                                            key=f"download_{plot_name}_med"
                                        )
                                else:
                                    # Display image plot
                                    st.image(plot_path, use_container_width=True)

                                    # Download button for image
                                    with open(plot_path, "rb") as file:
                                        st.download_button(
                                            label=f"📥 Download {plot_name}",
                                            data=file.read(),
                                            file_name=os.path.basename(plot_path),
                                            mime="image/png",
                                            key=f"download_{plot_name}_med"
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
        ["📚 Policy Gallery", "📄 Medical Records", "📋 Policy Conversion", "👤 Patient Compliance"]
    )

    # Route to appropriate page
    if page == "📚 Policy Gallery":
        policy_gallery_page()
    elif page == "📄 Medical Records":
        medical_record_page()
    elif page == "📋 Policy Conversion":
        policy_conversion_page()
    elif page == "👤 Patient Compliance":
        patient_compliance_page()

if __name__ == "__main__":
    main()
