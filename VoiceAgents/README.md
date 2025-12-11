# VoiceAgents - Healthcare Voice Triage System

A comprehensive multi-agent healthcare voice system for patient appointment management, symptom monitoring, medication education, and caregiver support.

## Overview

VoiceAgents is an AI-powered healthcare assistant that provides:
- **Appointment Management** - Schedule, reschedule, cancel, and check appointments
- **Symptom Triage** - RED/ORANGE/GREEN classification for emergency detection
- **Medication Education** - Side effects, interactions, dosing guidance
- **Symptom Monitoring** - Track patient-reported symptoms over time
- **Caregiver Support** - Generate weekly summaries for family caregivers

## System Impact

### Key Performance Metrics

| Metric | Result | Impact |
|--------|--------|--------|
| ⚡ **Response Time** | **<2 seconds** | Instant triage vs hours waiting for callbacks - immediate patient support 24/7 |
| 🚨 **Emergency Detection** | **96.8%** (30/31) | Catches life-threatening symptoms requiring immediate ER referral |
| 🎯 **Intent Accuracy** | **98.4%** (120/122) | Correctly understands patient needs and routes to appropriate care |

### Clinical Impact

- **Reduces Wait Times**: Patients receive instant responses instead of waiting hours for nurse callbacks
- **24/7 Availability**: Round-the-clock patient support reduces anxiety and improves outcomes
- **Early Emergency Detection**: 96.8% sensitivity for RED flag symptoms prevents delayed treatment
- **100% Policy Compliance**: Perfect enforcement of clinical rules (minor consent, referrals, telehealth eligibility)
- **Medication Safety**: 100% detection of high-risk scenarios (double dosing, serious drug interactions)
- **Response Quality**: 4.3/5 average rating from clinical review (86% rated good/excellent)

### Validated Performance

- **122 Test Cases**: Comprehensive validation across all agent capabilities
- **100% Routing Accuracy**: Perfect intent classification (confirmed by confusion matrices)
- **Zero False Positives**: 100% specificity for ORANGE/GREEN triage
- **Consistent Quality**: All interactions logged for clinical oversight and quality improvement

## Quick Start

**Recommended**: Use the LangGraph implementation for the most complete, production-ready experience.

```bash
cd VoiceAgents_langgraph
cp .env.example .env          # Add your API keys
pip install -r requirements.txt
python main.py
```

## Project Structure

```
VoiceAgents/
├── VoiceAgents_langgraph/       # ⭐ Main LangGraph implementation (RECOMMENDED)
│   ├── __init__.py                    # Package initialization
│   ├── state.py                        # TypedDict state schema for workflow
│   ├── workflow.py                     # LangGraph workflow definition and compilation
│   ├── main.py                         # CLI entry point (run directly: python main.py)
│   ├── database.py                     # Local database service using data/ folder
│   ├── .env                            # Environment variables (API keys) - create from .env.example
│   ├── .env.example                    # Environment template (safe to commit)
│   ├── requirements.txt                # Python dependencies
│   │
│   ├── policy/                         # Policy and safety configuration
│   │   ├── system_behavior.py          # Global system prompt and behavior
│   │   └── agents/                     # Agent-specific policies
│   │       ├── appointment_policy.json
│   │       ├── followup_policy.json
│   │       ├── medication_policy.json
│   │       ├── caregiver_policy.json
│   │       └── help_policy.json
│   │
│   ├── docs/                           # Documentation
│   │   └── Safety_and_Boundaries.md    # Safety and clinical boundaries documentation
│   │
│   ├── validation_datasets/             # Validation datasets for testing
│   │   ├── appointment_agent_validation.csv
│   │   └── medication_agent_validation.csv
│   │
│   ├── utils/                          # Utility modules folder
│   │   ├── __init__.py                 # Utilities (TTS, STT, timestamps) - exports: say, stt_transcribe, mic_listen_once, now_iso, chat_completion, etc.
│   │   ├── llm_provider.py             # Multi-provider LLM abstraction (OpenAI/Anthropic/Google)
│   │   └── logging_utils.py            # File logging utilities for all agents
│   │
│   ├── nodes/                          # LangGraph agent nodes
│   │   ├── __init__.py
│   │   ├── routing.py                  # Intent detection and routing logic
│   │   ├── appointment.py              # Appointment management with triage (STT/TTS)
│   │   ├── followup.py                 # Symptom monitoring with triage (STT/TTS)
│   │   ├── medication.py               # Medication Q&A (STT/TTS)
│   │   ├── caregiver.py                # Caregiver summary generation (STT/TTS)
│   │   └── help.py                     # General conversation and help (STT/TTS)
│   │
│   ├── data/                           # Local data files (self-contained)
│   │   ├── patients.csv                 # Patient records
│   │   ├── appointments.csv             # Appointment bookings
│   │   ├── prescriptions.csv            # Medication prescriptions
│   │   ├── caregivers.csv               # Caregiver information
│   │   ├── policy_config.json           # Business rules and policies
│   │   ├── symptom_codes.csv            # SNOMED symptom code mappings
│   │   ├── drug_knowledge.csv           # Medication knowledge base
│   │   └── generated_qna_examples.json   # Generated Q&A examples
│   │
│   ├── logs/                           # Runtime logs directory
│   │   ├── appointment_agent_log.jsonl  # Appointment interactions
│   │   ├── followup_agent_log.jsonl     # Symptom monitoring logs
│   │   ├── med_agent_log.jsonl          # Medication query logs
│   │   ├── caregiver_summaries.jsonl    # Caregiver summaries (JSON)
│   │   ├── caregiver_summaries.txt       # Caregiver summaries (Text)
│   │   ├── orchestration_log.jsonl      # Routing and orchestration logs
│   │   └── symptom_logs.csv             # Symptom tracking logs (auto-created)
│   │
│   ├── evaluation/                     # Evaluation scripts and results
│   │   ├── evaluate_langgraph.py        # LangGraph-specific evaluation
│   │   ├── evaluate_agents.py           # Original evaluation script
│   │   ├── benchmark_performance.py     # Performance benchmarking
│   │   ├── generate_report.py           # HTML report generation
│   │   ├── test_dataset.json            # Test dataset
│   │   ├── results/                     # Evaluation results
│   │   └── README.md                    # Evaluation documentation
│   │
│   ├── tests/                          # Test suite
│   │   ├── test_agents.py               # Agent tests
│   │   └── README.md                    # Tests documentation
│   │
│   └── prototype_demo/                  # Streamlit web UI demo
│       ├── streamlit_app.py             # Streamlit interface
│       └── README.md                    # Demo documentation
│
├── DOCUMENTATION/                      # Project documentation
│   ├── VOICE_AGENT_REPORT.md           # Detailed system report
│   ├── Nextsteps.md                    # Remaining work items
│   ├── Updates.md                      # Implementation change log
│   ├── EVALUATION_REPORT.md            # Evaluation results
│   └── Voice_Agent_Triage_Logic_Summary.md  # Triage system documentation
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

**Key Features:**
- **Standalone Package**: Complete independence from parent directory
- **LangGraph Architecture**: Graph-based workflow for healthcare interactions
- **STT/TTS Support**: Speech-to-text and text-to-speech enabled in all nodes
- **Comprehensive Logging**: All conversation flows logged to `logs/` directory
- **Multi-Provider LLM**: Supports OpenAI, Anthropic, and Google with configurable fallback
- **Full Functionality**: All agent functions from original VoiceAgents preserved

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

See the [Validation Datasets](#validation-datasets) section above for details.

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

# Initialize state
state: VoiceAgentState = {
    "user_input": "I am patient 10004235, check my appointment",
    "patient_id": "10004235",
    "intent": None,
    "parsed_data": {},
    "appointment_response": None,
    "followup_response": None,
    "medication_response": None,
    "caregiver_response": None,
    "help_response": None,
    "response": None,
    "voice_enabled": False,
    "session_id": "session_123",
    "timestamp": None,
    "log_entry": None
}

# Run workflow
result = voice_agent_workflow.invoke(state)
print(result["response"])

# Response will be in result["response"]
# Logs automatically written to logs/ directory
```

**Streamlit Demo**:
```bash
cd VoiceAgents_langgraph/prototype_demo
streamlit run streamlit_app.py
```

## CLI Commands

When running `main.py`:

- `:voice on | :voice off` - Toggle text-to-speech output (all responses)
- `pid <8digit>` - Set default patient ID context (e.g., `pid 10004235`)
- `:stt <path_to_audio.wav/mp3>` - Transcribe audio file then process
- `:mic on` - Record from microphone and process (STT)
- `quit` - Exit the application

### Example Conversation

```
You (or command): :voice on
[voice] Enabled

You (or command): pid 10004235
[context] patient_id set to 10004235

You (or command): check my appointment
Agent: Great! I can confirm that your Follow-up - Cardiology with Dr. Johnson on October 08 at 02:20 PM is scheduled and confirmed.
[Spoken via TTS]

You (or command): I feel dizzy 7/10
Agent: I've noted that you're experiencing dizziness. With a severity of 7 out of 10, I'm going to have a nurse call you today...
[Spoken via TTS]

You (or command): :stt audio/patient_recording.wav
[stt] → I want to reschedule my appointment
Agent: I'd be happy to help you reschedule! Here are some available times...
```

## Evaluation

### Running Evaluation

**From inside VoiceAgents_langgraph/ directory:**

```bash
cd VoiceAgents_langgraph

# Option 1: Run evaluation script directly
python evaluation/evaluate_langgraph.py

# Option 2: Run as module (from VoiceAgents_langgraph/)
python -m evaluation.evaluate_langgraph
```

The evaluation script will:
1. Load test cases from `evaluation/test_dataset.json`
2. Run orchestration, medication, and end-to-end tests
3. Generate confusion matrices for classification tasks
4. Save results to `evaluation/results/`

### Evaluation Results

After running, results are saved to `evaluation/results/`:
- **evaluation_results.json** - Detailed test results for each agent
- **confusion_matrices.json** - Confusion matrices for classification tasks
- **performance_benchmark.json** - Performance metrics (if using benchmark script)
- **evaluation_report.html** - HTML report (if generated)

### Test Dataset Format

The test dataset (`evaluation/test_dataset.json`) should follow this structure:

```json
{
  "orchestration_tests": [
    {
      "id": "orch_1",
      "query": "check my appointment",
      "expected_agent": "appointment",
      "patient_id": "10004235"
    },
    {
      "id": "orch_2",
      "query": "I feel dizzy",
      "expected_agent": "followup",
      "patient_id": "10004235"
    }
  ],
  "medication_tests": [
    {
      "id": "med_1",
      "query": "what are the side effects of metformin?",
      "expected_intent": "side_effect",
      "expected_risk": "GREEN",
      "patient_id": "10004235"
    },
    {
      "id": "med_2",
      "query": "I forgot to take my medication",
      "expected_intent": "missed_dose",
      "expected_risk": "ORANGE",
      "patient_id": "10004235"
    }
  ],
  "e2e_tests": [
    {
      "id": "e2e_1",
      "query": "I am patient 10004235, check my appointment",
      "expected_intent": "appointment",
      "patient_id": "10004235"
    }
  ]
}
```

### Additional Evaluation Scripts

- **benchmark_performance.py** - Run performance benchmarks
```bash
python evaluation/benchmark_performance.py
```

- **generate_report.py** - Generate HTML evaluation report
```bash
python evaluation/generate_report.py
```

- **evaluate_agents.py** - Original evaluation script (may need parent directory context)

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
- `symptom_logs.csv` - Symptom tracking logs
- `followup_agent_log.jsonl` - Symptom reports
- `med_agent_log.jsonl` - Medication queries
- `caregiver_summaries.jsonl` - Caregiver summaries
- `orchestration_log.jsonl` - Routing decisions

## Configuration

### Environment Variables (.env)

Edit `.env` to configure:

```bash
# Provider priority
LLM_PROVIDER=anthropic
LLM_FALLBACK_ORDER=anthropic,google,openai   
# You can change LLM_PROVIDER and LLM_FALLBACK_ORDER here. If the change doesn't work, you might need to modify utils/llm_provider.py

# Models
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
GOOGLE_MODEL=gemini-2.0-flash

# API keys 
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Voice
VOICE_ENABLED=false          # Enable TTS by default

# Logging
LOG_LEVEL=INFO
```

### LLM Provider Fallback System

The system uses a configurable fallback sequence defined by `LLM_FALLBACK_ORDER` in `.env`. If the primary provider fails (rate limits, API errors), the system automatically tries the next provider in the sequence.

**Default Behavior:**
- Primary provider: `anthropic` (from `LLM_PROVIDER`)
- Fallback sequence: `anthropic -> google -> openai` (from `LLM_FALLBACK_ORDER`)

**Customization:**
Edit `.env` to change the fallback order:
```bash
LLM_PROVIDER=anthropic
LLM_FALLBACK_ORDER=anthropic,google,openai
```

The system will try providers in the order specified, only using providers that have valid API keys configured.

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

### LangGraph Workflow

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

### Core Components

**state.py**: Defines the `VoiceAgentState` TypedDict schema that flows through the graph, containing user input, parsed intent, patient ID, agent responses, voice settings, and logging information.

**workflow.py**: Creates and configures the LangGraph workflow by adding nodes, setting entry points, and defining conditional routing based on intent classification.

**main.py**: Command-line interface that handles user input, manages session state, invokes the workflow, and provides voice I/O commands (TTS toggle, microphone, audio file transcription).

**database.py**: Self-contained database service that reads/writes CSV files from the local `data/` folder. Provides methods for patient lookup, appointment queries, prescription retrieval, symptom logging, and trend analysis.

### Utils Module

**utils/__init__.py**: Shared utility functions exported from the utils package:
- `say(text, voice=False)` - Text-to-speech output
- `stt_transcribe(path)` - Speech-to-text from audio file
- `mic_listen_once()` - Speech-to-text from microphone
- `now_iso()` - Timestamp generation
- `chat_completion()` - LLM chat completion (re-exported from llm_provider)
- `audio_transcribe()` - Audio transcription (re-exported from llm_provider)

**utils/llm_provider.py**: Unified interface for multiple LLM providers (OpenAI, Anthropic, Google). Handles client initialization, message formatting across providers, and audio transcription. Configurable via `.env` file.

**utils/logging_utils.py**: Centralized logging utilities that write agent-specific logs to `logs/` directory:
- `log_appointment(entry)` - Log appointment interactions
- `log_followup(entry)` - Log symptom monitoring
- `log_medication(entry)` - Log medication queries
- `log_caregiver(entry, write_txt=True)` - Log caregiver summaries
- `log_orchestration(entry)` - Log routing and orchestration

### Agent Nodes

All nodes support **STT (Speech-to-Text)** input via `main.py` commands and **TTS (Text-to-Speech)** output when `voice_enabled` is True:

**nodes/routing.py**: Parses user input to determine intent (appointment/followup/medication/caregiver/help) and extracts 8-digit patient IDs. Uses LLM with rule-based fallback. Prioritizes appointment keywords when scheduling is mentioned alongside symptoms.

**nodes/appointment.py** (STT/TTS): Handles appointment operations including status checks, rescheduling, cancellation, and new scheduling. Implements comprehensive triage logic (RED/ORANGE/GREEN) based on symptoms and enforces business rules (minor consent, referral requirements, telehealth policies, post-op windows).

**nodes/followup.py** (STT/TTS): Logs patient-reported symptoms with severity scores. Uses LLM-powered symptom extraction with keyword fallback. Implements triage system (RED/ORANGE/GREEN) to flag serious symptoms. All interactions logged to `logs/followup_agent_log.jsonl`.

**nodes/medication.py** (STT/TTS): Answers medication questions including side effects, missed dose advice, drug interactions, food guidance, and contraindications. Assesses risk levels (RED/ORANGE/GREEN). All interactions logged to `logs/med_agent_log.jsonl`.

**nodes/caregiver.py** (STT/TTS): Generates weekly caregiver summaries by aggregating symptom trends and medication adherence data. Only processes summaries for patients with linked caregivers and consent on file. Logs to `logs/caregiver_summaries.jsonl` and `.txt`.

**nodes/help.py** (STT/TTS): Provides general LLM-powered conversation for greetings, questions, and non-specific requests. Falls back to static help message if LLM unavailable.

## Testing

### Running Tests

**From inside VoiceAgents_langgraph/ directory:**

```bash
cd VoiceAgents_langgraph

# From VoiceAgents_langgraph/ directory
pytest tests/test_agents.py -v -s
```

The test suite includes:
- Follow-up agent triage tests (GREEN/ORANGE/RED)
- Appointment agent tests
- Medication agent tests
- Routing/orchestration tests
- Workflow integration tests
- Triage consistency tests

All tests verify that the system maintains consistent behavior after changes.


### What's Included

✅ All data files in `data/`  
✅ All dependencies in `requirements.txt`  
✅ Virtual environment in `.venv/` (if copied)  
✅ Environment configuration in `.env`  
✅ All logs in `logs/` 
✅ Evaluation scripts in `evaluation/`  
✅ Complete STT/TTS support throughout  
✅ Comprehensive logging infrastructure  

**No external dependencies on parent directory!**


## License

Part of the CMU x Zyter Capstone Project.
