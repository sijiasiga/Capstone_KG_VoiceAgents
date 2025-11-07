# VoiceAgents - Healthcare Voice Triage System

A comprehensive multi-agent healthcare voice system for patient appointment management, symptom monitoring, medication education, and caregiver support.

## Overview

VoiceAgents is an AI-powered healthcare assistant that provides:
- **Appointment Management** - Schedule, reschedule, cancel, and check appointments
- **Symptom Triage** - RED/ORANGE/GREEN classification for emergency detection
- **Medication Education** - Side effects, interactions, dosing guidance
- **Symptom Monitoring** - Track patient-reported symptoms over time
- **Caregiver Support** - Generate weekly summaries for family caregivers

## Quick Start

**Recommended**: Use the LangGraph implementation for the most complete, production-ready experience.

```bash
cd VoiceAgents_langgraph
cp .env.example .env          # Add your API keys
pip install -r requirements.txt
python main.py
```

See [VoiceAgents_langgraph/README.md](VoiceAgents_langgraph/README.md) for detailed documentation.

## Project Structure

```
VoiceAgents/
├── VoiceAgents_langgraph/       # ⭐ Main LangGraph implementation (RECOMMENDED)
│   ├── nodes/                   # Agent implementations
│   ├── data/                    # Patient data and knowledge bases
│   ├── validation_datasets/     # Validation test cases for client review
│   ├── evaluation/              # Evaluation scripts and results
│   ├── main.py                  # CLI entry point
│   └── README.md                # Full documentation
│
├── appointment_agent/           # Original standalone appointment agent
├── followup_agent/              # Original standalone symptom monitoring
├── medication_agent/            # Original standalone medication Q&A
├── caregiver_agent/             # Original standalone caregiver summaries
├── orchestration_agent/         # Original intent routing agent
├── common_data/                 # Shared data files
├── evaluation/                  # Original evaluation scripts
└── prototype_demo/              # Original demo interface
```

## Implementations

### VoiceAgents_langgraph (Recommended)

**Status**: Production-ready, fully integrated

The LangGraph implementation is a complete, standalone system with:
- Graph-based workflow orchestration
- Full STT (Speech-to-Text) and TTS (Text-to-Speech) support
- Comprehensive logging infrastructure
- Multi-provider LLM support (OpenAI, Anthropic, Google)
- Validation datasets for client feedback
- Complete independence (can be moved anywhere)

**Best for**: Production deployment, client demos, validation testing

[Full Documentation](VoiceAgents_langgraph/README.md)

### Original Agents (Legacy)

**Status**: Reference implementation, individual agent testing

The original implementation consists of standalone agents in separate directories:
- `appointment_agent/` - Appointment management
- `followup_agent/` - Symptom monitoring
- `medication_agent/` - Medication education
- `caregiver_agent/` - Caregiver summaries
- `orchestration_agent/` - Intent routing

**Best for**: Understanding individual agent logic, isolated testing

Each agent has its own README with specific documentation.

## Core Features

### 1. Appointment Agent

Handles all appointment operations with intelligent triage:
- Check appointment status
- Schedule new appointments
- Reschedule existing appointments
- Cancel appointments
- **RED/ORANGE/GREEN triage** for emergency detection
- Policy enforcement (minor consent, referrals, telehealth, post-op windows)

**Example**:
```
User: I have chest pain, when can I come in?
Agent: [HIGH RISK - RED] You need immediate medical attention.
       Please go to the emergency department or call 911...
```

### 2. Symptom Monitoring (Followup Agent)

Tracks patient-reported symptoms with severity scoring:
- Log symptoms with 0-10 severity scale
- Track fever temperatures
- Detect emergency symptoms (chest pain, SOB, etc.)
- Trend analysis for caregiver summaries
- **RED/ORANGE/GREEN triage** classification

**Example**:
```
User: I'm feeling dizzy, maybe 7/10
Agent: [ORANGE] I've logged your dizziness at severity 7/10.
       A nurse will call you today to discuss your symptoms...
```

### 3. Medication Education

Answers medication questions with risk assessment:
- Side effects information
- Missed dose guidance
- Drug interaction warnings
- Food and timing instructions
- Contraindication alerts
- **RED/ORANGE/GREEN risk** assessment

**Example**:
```
User: What if I took two doses of my blood pressure medication?
Agent: [HIGH RISK - RED] Please seek immediate medical care.
       Taking double doses can cause dangerous blood pressure drops...
```

### 4. Caregiver Support

Generates weekly summaries for family caregivers:
- Symptom trend analysis
- Medication adherence tracking
- Appointment reminders
- Privacy-compliant (consent required)

### 5. Intelligent Routing

Automatic intent detection routes queries to the correct agent:
- Natural language understanding
- Multi-intent handling
- Patient ID extraction
- LLM-powered with rule-based fallback

## Triage System

Three-tier classification for patient safety:

### RED (Emergency)
- Chest pain/tightness
- Shortness of breath
- High fever (≥101.5°F)
- Severe pain (≥8/10)
- Wound complications
- Neurological deficits

**Action**: Emergency department referral, immediate provider alert

### ORANGE (Concerning)
- Moderate pain (5-7/10)
- Low-grade fever (99.5-101.4°F)
- Dizziness
- Wound redness/swelling

**Action**: Nurse callback scheduled, tentative appointment hold

### GREEN (Routine)
- Mild symptoms
- General questions
- Normal follow-up

**Action**: Logged for provider review

## Validation Datasets

Client-ready validation datasets for quality assurance:

- **validation_datasets/appointment_agent_validation.csv** - 64 test cases
- **validation_datasets/medication_agent_validation.csv** - 58 test cases

Each dataset contains **real agent responses** from live execution, including:
- Intent classification accuracy
- Triage tier assignments
- Policy enforcement results
- Complete agent responses

**Current Performance**:
- Appointment triage accuracy: 96.8%
- Medication risk assessment: Full coverage across all risk tiers

See [Validation Datasets Documentation](VoiceAgents_langgraph/README.md#-validation-datasets) for details.

## Getting Started

### Prerequisites

- Python 3.9+ (required for LangGraph)
- OpenAI API key (or Anthropic/Google)
- Basic understanding of healthcare workflows

### Installation (LangGraph)

```bash
# Navigate to main implementation
cd VoiceAgents_langgraph

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running the System

**CLI Mode**:
```bash
cd VoiceAgents_langgraph
python main.py
```

**Programmatic Usage**:
```python
from VoiceAgents_langgraph.workflow import voice_agent_workflow
from VoiceAgents_langgraph.state import VoiceAgentState

state: VoiceAgentState = {
    "user_input": "I am patient 10004235, check my appointment",
    "patient_id": "10004235",
    # ... other fields
}

result = voice_agent_workflow.invoke(state)
print(result["response"])
```

**Streamlit Demo**:
```bash
cd VoiceAgents_langgraph/prototype_demo
streamlit run streamlit_app.py
```

## CLI Commands

When running `main.py`:

- `:voice on | :voice off` - Toggle text-to-speech
- `pid <8digit>` - Set patient ID context
- `:stt <audio_file>` - Transcribe audio file
- `:mic on` - Record from microphone
- `quit` - Exit

## Evaluation

Run comprehensive evaluation suite:

```bash
cd VoiceAgents_langgraph
python evaluation/evaluate_langgraph.py
```

Results saved to `evaluation/results/`:
- Confusion matrices
- Accuracy metrics
- Performance benchmarks
- HTML reports

## Data Files

All patient data stored in `VoiceAgents_langgraph/data/`:

- `patients.csv` - Patient demographics
- `appointments.csv` - Appointment bookings
- `prescriptions.csv` - Medication records
- `drug_knowledge.csv` - Medication knowledge base
- `symptom_codes.csv` - SNOMED symptom mappings
- `policy_config.json` - Business rules

## Logging

All interactions logged to `VoiceAgents_langgraph/logs/`:

- `appointment_agent_log.jsonl` - Appointment interactions
- `followup_agent_log.jsonl` - Symptom reports
- `med_agent_log.jsonl` - Medication queries
- `caregiver_summaries.jsonl` - Caregiver summaries
- `orchestration_log.jsonl` - Routing decisions

## Configuration

Edit `.env` to configure:

```bash
# LLM Provider
LLM_PROVIDER=openai          # Options: openai, anthropic, google

# API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=optional
GOOGLE_API_KEY=optional

# Models
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GOOGLE_MODEL=gemini-pro

# Voice
VOICE_ENABLED=false          # Enable TTS by default

# Logging
LOG_LEVEL=INFO
```

## Use Cases

### For Healthcare Providers
- Reduce phone call volume
- Triage patient concerns automatically
- Track symptom progression
- Improve appointment scheduling efficiency

### For Patients
- 24/7 appointment access
- Medication education on-demand
- Symptom tracking and monitoring
- Emergency situation detection

### For Caregivers
- Weekly patient summaries
- Medication adherence tracking
- Early warning for concerning symptoms

## Architecture

**LangGraph Workflow**:
```
User Input → Routing Node → Intent Detection
                ↓
    ┌───────────┴───────────┐
    ↓                       ↓
Appointment Agent    Medication Agent
    ↓                       ↓
Followup Agent      Caregiver Agent
    ↓                       ↓
Help Agent          Response
```

Each node:
- Receives state from previous node
- Processes specific intent
- Updates shared state
- Logs interaction
- Returns updated state

## Troubleshooting

**No module named 'langgraph'**:
```bash
pip install -r requirements.txt
```

**API key errors**:
```bash
cp .env.example .env
# Add your API keys to .env
```

**Python version issues**:
```bash
python --version  # Must be 3.9+
```

**TTS/STT not working**:
```bash
# macOS
brew install portaudio
# Then
pip install pyttsx3 speechrecognition pyaudio
```

See [VoiceAgents_langgraph/README.md](VoiceAgents_langgraph/README.md) for detailed troubleshooting.

## Contributing

This project is part of the CMU x Zyter Capstone Project.

## Documentation

- **Main Documentation**: [VoiceAgents_langgraph/README.md](VoiceAgents_langgraph/README.md)
- **Evaluation**: [VoiceAgents_langgraph/evaluation/README.md](VoiceAgents_langgraph/evaluation/README.md)
- **Prototype Demo**: [VoiceAgents_langgraph/prototype_demo/README.md](VoiceAgents_langgraph/prototype_demo/README.md)

## License

Part of the CMU x Zyter Capstone Project.
