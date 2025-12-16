# Healthcare AI Systems
## CMU x Zyter Capstone Project

This repository contains two complementary healthcare AI systems developed as part of the Carnegie Mellon University and Zyter Health capstone project.

---

## 🎯 Project Overview

### 🎤 Voice Agents
**AI-powered voice triage and patient support system**

- 24/7 appointment management and scheduling
- Intelligent symptom triage (RED/ORANGE/GREEN classification)
- Medication education and safety monitoring
- Caregiver support with automated summaries
- Natural language understanding for healthcare conversations

**→ [Explore Voice Agents System](./VoiceAgents/README.md)**

### 🔗 Knowledge Graph
**Policy-based medical coverage and prior authorization system**

- Medical policy extraction and representation
- Prior authorization decision support
- Healthcare coverage determination
- Clinical guideline knowledge base

**→ [View Knowledge Graph System](./KG/README.md)**

---

## 🚀 Quick Start

### Voice Agents

```bash
cd VoiceAgents/VoiceAgents_langgraph
cp .env.example .env  # Add your API keys
pip install -r requirements.txt
python main.py
```

### Knowledge Graph

```bash
cd KG
pip install -r requirements.txt
```
Before running, create `api.json` in the KG directory:
```json
{
  "gemini": "your-gemini-api-key-here"
}
```
then run this in the terminal

```bash
streamlit run streamlit_final.py
```
---

## 📂 Repository Structure

```
Capstone_KG_VoiceAgents/
├── VoiceAgents/              # Voice triage system (main project)
│   ├── VoiceAgents_langgraph/    # Production implementation
│   │   ├── main.py               # Entry point
│   │   ├── nodes/                # Agent implementations
│   │   ├── data/                 # Patient data and knowledge base
│   │   ├── evaluation/           # Test datasets and results
│   │   └── docs/                 # System documentation
│   └── DOCUMENTATION/            # Project reports and analysis
│
└── KG/                       # Knowledge Graph system
    ├── patient_kg.py               # Patient data visualizer with code mapping
    ├── patient_rule_kg_interactive.py  # Patient vs policy evaluator (more detailed KG)
    ├── policy_rule_kg_interactive.py   # Policy rule generator (more detailed KG)
    ├── process_policy.py           # Agents Orchestration for Policy Extraction
    ├── process_patient_record.py   # Patient Data Extraction Agents
    ├── streamlit_final.py          # Interactive web application with more funcs
    ├── prompt_generator.py         # generate evaluation prompt for LLM-based Method
    ├── Database                    # Database management system
    ├── OCR                         # Medical record processing
    ├── prompts                     # Prompts for Agents
    ├── NCD_LCD_Syn_data/           # Test Policies (Source data)
    ├── Run_Time_Policy /              # Results of Agent Orchestration (Policy extraction outputs)
    ├── Run_Time_Patient /              # Results of Patient Compliance
    └── scripts/                    # Automation scripts
```

---

## 📚 Documentation

### Voice Agents
- **[📖 Documentation Guide](./VoiceAgents/DOCUMENTATION/START_HERE.md)** - Navigation and getting started
- **[System Overview](./VoiceAgents/README.md)** - Complete feature documentation
- **[Evaluation Report](./VoiceAgents/DOCUMENTATION/EVALUATION_REPORT.md)** - Performance analysis and validation
- **[Technical Architecture](./VoiceAgents/DOCUMENTATION/VOICE_AGENT_REPORT.md)** - System design and implementation

### Knowledge Graph
- **[System Overview](./KG/README.md)** - KG system documentation and features

---

## 🎓 Project Team

**Carnegie Mellon University x Zyter Health**
Capstone Project - Healthcare AI Systems

---

## 📧 Contact

For questions or more information, please refer to the documentation or contact the project team.
