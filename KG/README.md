# Medical Policy Knowledge Graph Generator

A Python toolkit for generating and visualizing knowledge graphs from medical policies and patient data. This project focuses on bariatric surgery policies and creates visualizations to understand complex medical decision rules.

## 🚀 Quick Start

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Run the Streamlit web app:**

```bash
streamlit run streamlit_app.py
```

## 📁 Project Structure

```
├── patient_kg.py               # Patient data visualizer with code mapping
├── patient_rule_kg.py          # Patient vs policy evaluator  
├── policy_rule_kg.py           # Policy rule generator
├── process_policy.py           # Agents Orchestration for Policy Extraction
├── streamlit_app.py            # Interactive web application
├── Database                    # Database management system
├── OCR                         # Medical record processing
├── prompts                     # Prompts for Agents
├── patient_data/               # Patient case studies
│   ├── patient_8472202544/     # Patient case 1 (ELIGIBLE)
│   ├── patient_9384202577/     # Patient case 2 (NOT ELIGIBLE)
│   └── patient_*/              # Additional patient cases
├── NCD_LCD_Syn_data/           # Test Policies (Source data)
│   ├── L34106/                 # LCD Policy 34106 - Vertebral Augmentation
│   │   ├── LCD - ... (L34106).pdf
│   │   ├── L34106_Record_001.pdf - L34106_Record_*.pdf   # Synthetic patient records
│   │   └── L34106_Summary.xlsx # Policy summary data
├── Policies_test/              # Results of Agent Orchestration (Policy extraction outputs)
│   ├── Policy_LCD_34106/       # Extracted policy data for L34106
│   │   ├── Policy_LCD_34106.txt          # OCR extracted policy text
│   │   ├── Data_dictionary_LCD_34106.json    # Extracted data fields
│   │   ├── Policy_LCD_34106.json            # Extracted policy conditions
│   │   ├── SQL_LCD_34106.txt               # Generated SQL queries
│   │   ├── Info_LCD_34106.json             # Policy metadata
│   │   ├── policy_rule_kg_LCD_34106.png    # Policy knowledge graph visualization
│   │   ├── policy_rule_kg_nodes.json       # KG node definitions
│   │   └── policy_rule_kg_edges.json       # KG edge definitions
├── test1/                      # Complete working example (Bariatric Surgery Policy CGSURG83)
│   ├── Policy_CGSURG83/        # Policy extraction outputs
│   │   ├── Medical_Policy_CGSURG83.txt    # OCR extracted policy text
│   │   ├── Data_dictionary_CGSURG83.json  # Extracted data fields
│   │   ├── Policy_CGSURG83.json           # Extracted policy conditions
│   │   ├── SQL_CGSURG83.txt               # Generated SQL queries
│   │   ├── Codes_CGSURG83.txt             # Medical codes mapping
│   │   └── policy_rule_kg.png             # Policy knowledge graph visualization
│   ├── Data_dictionary.json        # Initial data dictionary template
└── scripts/                    # Automation scripts
```

## 📋 Policy Rule Extraction: Bariatric Surgery

### Policy Extraction Agents Workflow

![Policy Extraction Agents](Figures/policy_extraction_agents.png)

The [`/test1`](test1) directory contains a complete working example analyzing bariatric surgery eligibility.

### 1. Data Field Extraction Agent

#### Input

1. **Bariatric Surgery Policy**: https://www.anthem.com/medpolicies/abc/active/gl_pw_d085821.html
2. [**Initial Data Dictionary**](test1/Data_dictionary.json):

```json
[
    {
      "name": "patient_id",
      "type": "string",
      "description": "Unique patient identifier",
      "section": "Demographics"
    }
]
```

#### Output

1. **Data Dictionary JSON**: [Data_dictionary_CGSURG83.json](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/KG/test1/Policy_CGSURG83/Data_dictionary_CGSURG83.json)

### 2. Policy Extraction Agent

#### Input

1. **Bariatric Surgery Policy**: https://www.anthem.com/medpolicies/abc/active/gl_pw_d085821.html
2. **Data Dictionary JSON**: [Data_dictionary_CGSURG83.json](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/KG/test1/Policy_CGSURG83/Data_dictionary_CGSURG83.json)

#### Output

1. **Policy Condition JSON**: [Policy_CGSURG83.json](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/KG/test1/Policy_CGSURG83/Policy_CGSURG83.json)

### 3. SQL Convertion Agent

#### Input

1. **Policy Condition JSON**: [Policy_CGSURG83.json](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/KG/test1/Policy_CGSURG83/Policy_CGSURG83.json)

#### Output

1. **SQL**: [SQL_CGSURG83.txt](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/KG/test1/Policy_CGSURG83/SQL_CGSURG83.txt)

```sql
WHERE patient_age >= 18 
  AND (patient_bmi >= 40.0 OR (patient_bmi >= 35.0 AND comorbidity_flag = TRUE))
  AND weight_loss_program_history = TRUE
  AND conservative_therapy_attempt = TRUE
  AND preop_medical_clearance = TRUE
  AND preop_psych_clearance = TRUE
  AND preop_education_completed = TRUE
  AND treatment_plan_documented = TRUE
```

## 🤖 Policy Extraction Pipeline (process_policy.py)

This script implements an end-to-end policy extraction pipeline using Gemini 2.5-Flash, chaining three agents together:

1. **DataField Agent** - Extracts structured data fields from policy text
2. **Policy Agent** - Extracts policy conditions and restrictions
3. **SQL Agent** - Converts policy conditions to executable SQL

### Setup

Before running, create `api.json` in the root directory:

```json
{
  "gemini": "your-gemini-api-key-here"
}
```

### Usage

```bash
cd KG
bash scripts/run_process_policy.sh
```

The script will:

- Extract text from PDF using OCR
- Run all 3 Gemini agents in sequence
- Output files with naming format: `{Type}_{policy_id}.{ext}`

### Output Files

- `Policy_{policy_id}.txt` - OCR extracted policy text
- `Data_dictionary_{policy_id}.json` - Extracted data fields
- `Policy_{policy_id}.json` - Extracted policy conditions
- `SQL_{policy_id}.txt` - Generated SQL queries

### Result of Agent Orchestration

```bash
bash scripts/run_process_all_policies.sh
```
Results are saved under [Policies_test](Policies_test)


### Data Field Validation

```bash
cd KG
python DataField_Valid_Agent.py
```

Validates extracted data fields against policy text for accuracy and completeness.

## 📊 Patient-Policy Compliance

The system processes medical policies and patient data through three main phases:

```
Phase 1: Policy Analysis
Input: Policy rules (policy json/sql)
Output: Policy knowledge graph

Phase 2: Patient Analysis  
Input: Patient data (patient record json)
Output: Patient knowledge graph

Phase 3: Compliance Evaluation
Input: Patient data + Policy rules
Output: Compliance report + Visualization
```

### Generated Outputs

**1. Policy Knowledge Graph** (`Policy_CGSURG83/policy_rule_kg.png`)
![Bariatric Surgery Policy KG](test1/Policy_CGSURG83/policy_rule_kg.png)

**2. Patient Knowledge Graphs**

### ✅ Patient 8472202544 - ELIGIBLE

[PDF](patient_data/patient_8472202544/MR_2.pdf)--[OCR](OCR/pdf_ocr.py)--[Parser](OCR/medical_record_parser.py)-->[JSON](patient_data/patient_8472202544/Patient_data_dictionary_8472202544.json)

```json
{
  "patient_id": "8472202544",
  "patient_age": 47,
  "patient_bmi": 42.4,
  "comorbidity_flag": true,
  "weight_loss_program_history": true,
  "conservative_therapy_attempt": true,
  "preop_medical_clearance": true,
  "preop_psych_clearance": true,
  "preop_education_completed": true,
  "treatment_plan_documented": true,
  "procedure_code_CPT": "43846",
  "procedure_code_ICD10PCS": "0D160ZA",
  "diagnosis_code_ICD10": "E66.01"
}
```

![Patient 8472202544 KG](patient_data/patient_8472202544/patient_kg.png)

### ❌ Patient 9384202577 - NOT ELIGIBLE

[PDF](patient_data/patient_9384202577/MR_3.pdf)--[OCR](OCR/pdf_ocr.py)--[Parser](OCR/medical_record_parser.py)-->[JSON](patient_data/patient_9384202577/Patient_data_dictionary_9384202577.json)

```json
{
  "patient_id": "9384202577",
  "patient_age": 40,
  "patient_bmi": 27.1,
  "comorbidity_flag": true,
  "weight_loss_program_history": true,
  "conservative_therapy_attempt": true,
  "preop_medical_clearance": true,
  "preop_psych_clearance": true,
  "preop_education_completed": false,
  "treatment_plan_documented": true,
  "procedure_code_CPT": "43775",
  "procedure_code_ICD10PCS": "0DB64Z3",
  "diagnosis_code_ICD10": "E66.01"
}
```

![Patient 9384202577 KG](patient_data/patient_9384202577/patient_kg.png)

**3. Compliance Reports**

### ✅ Patient 8472202544 - ELIGIBLE

**Visualization:**
![Patient 8472202544 - Bariatric KG](patient_data/patient_8472202544/patient_rule_kg.png)

**Compliance Report** (`patient_data/patient_8472202544/pat_8472202544_pol_CGSURG83.json`):

```json
{
  "patient_id": "8472202544",
  "policy_id": "CGSURG83", 
  "patient_met_policy": true,
  "conditions": [
    {
      "condition": "Age requirement: Individual is 18 years or older.",
      "rule": "patient_age >= 18",
      "logic": "AND",
      "is_met": true,
      "logically_met": true,
      "logical_status": "met"
    },
    {
      "condition": "BMI 40 or greater.",
      "rule": "patient_bmi >= 40.0",
      "logic": "OR",
      "is_met": true,
      "logically_met": true,
      "logical_status": "met"
    }
  ]
}
```

### ❌ Patient 9384202577 - NOT ELIGIBLE

**Visualization:**
![Patient 9384202577 - Bariatric KG](patient_data/patient_9384202577/patient_rule_kg.png)

**Compliance Report** (`patient_data/patient_9384202577/pat_9384202577_pol_CGSURG83.json`):

```json
{
  "patient_id": "9384202577",
  "policy_id": "CGSURG83",
  "patient_met_policy": false,
  "conditions": [
    {
      "condition": "Age requirement: Individual is 18 years or older.",
      "rule": "patient_age >= 18",
      "logic": "AND",
      "is_met": true,
      "logically_met": true,
      "logical_status": "met"
    },
    {
      "condition": "BMI 40 or greater.",
      "rule": "patient_bmi >= 40.0",
      "logic": "OR",
      "is_met": false,
      "logically_met": true,
      "logical_status": "logically_met_by_other_or"
    },
    {
      "condition": "Pre-operative education completed (risks, benefits, expectations, need for long-term follow-up, adherence to behavioral modifications).",
      "rule": "preop_education_completed = TRUE",
      "logic": "AND",
      "is_met": false,
      "logically_met": false,
      "logical_status": "not_met"
    }
  ]
}
```

## 🌐 Streamlit Web Application

The `streamlit_app.py` provides an interactive web interface for the complete workflow:

### Features:

- **📄 Medical Records Page**: Upload PDFs, extract text, parse patient data, generate knowledge graphs
- **🗄️ SQL Queries Page**: View database, run policy filters, manage patient records

### Usage:

```bash
streamlit run streamlit_app.py
```

### Screenshots:

**Medical Records Processing Page:**
![Streamlit Medical Records Page](Figures/streamlit1.jpg)

**SQL Queries & Database Management Page:**
![Streamlit SQL Queries Page](Figures/streamlit2.jpg)

## 📝 TODO

- [X] **Agents Orchestration**: Finish multi-agent coordination
- [X] **Policy Extraction Automation**: End-to-end automation from PDF input to KG generation
- [ ] **Refinement of Policy OCR**: Enhance accuracy and robustness of medical policy text extraction
- [ ] **Refinement of Patient Record OCR**: Improve extraction quality from patient medical records
- [ ] **Refinement of Code Base**: Code optimization, documentation, and maintainability improvements
- [ ] **Validation Agent**: Design agents to evaluate the results for each agents
- [ ] **Streamlit Interface**: Add Policy Extraction Function
- [ ] **Interactive Interface**: KG plots
