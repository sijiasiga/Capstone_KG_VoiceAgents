# VoiceAgents LangGraph Implementation

A **standalone, independent** LangGraph-based implementation of the VoiceAgents healthcare voice triage system. This package can be moved anywhere and run independently with full STT (Speech-to-Text) and TTS (Text-to-Speech) support throughout all conversation flows.

## 🎯 Key Features

- **Standalone Package**: Complete independence from parent directory
- **LangGraph Architecture**: Graph-based workflow for healthcare interactions
- **STT/TTS Support**: Speech-to-text and text-to-speech enabled in all nodes
- **Comprehensive Logging**: All conversation flows logged to `logs/` directory
- **Multi-Provider LLM**: Supports OpenAI, Anthropic, and Google
- **Full Functionality**: All agent functions from original VoiceAgents preserved

## 📁 File Structure

```
VoiceAgents_langgraph/
├── __init__.py                    # Package initialization
├── state.py                        # TypedDict state schema for workflow
├── workflow.py                     # LangGraph workflow definition and compilation
├── main.py                         # CLI entry point (run directly: python main.py)
├── database.py                     # Local database service using data/ folder
├── .env                            # Environment variables (API keys) - create from .env.example
├── .env.example                    # Environment template (safe to commit)
├── .venv/                          # Virtual environment (if copied)
├── .gitignore                      # Git ignore rules
├── requirements.txt                # Python dependencies
│
├── utils/                          # Utility modules folder
│   ├── __init__.py                 # Utilities (TTS, STT, timestamps) - exports: say, stt_transcribe, mic_listen_once, now_iso, chat_completion, etc.
│   ├── llm_provider.py             # Multi-provider LLM abstraction (OpenAI/Anthropic/Google)
│   └── logging_utils.py            # File logging utilities for all agents
│
├── nodes/                          # LangGraph agent nodes
│   ├── __init__.py
│   ├── routing.py                  # Intent detection and routing logic
│   ├── appointment.py              # Appointment management with triage ✅ STT/TTS
│   ├── followup.py                 # Symptom monitoring with triage ✅ STT/TTS
│   ├── medication.py               # Medication Q&A ✅ STT/TTS
│   ├── caregiver.py                # Caregiver summary generation ✅ STT/TTS
│   └── help.py                     # General conversation and help ✅ STT/TTS
│
├── data/                           # Local data files (self-contained)
│   ├── patients.csv                 # Patient records
│   ├── appointments.csv             # Appointment bookings
│   ├── prescriptions.csv            # Medication prescriptions
│   ├── caregivers.csv               # Caregiver information
│   ├── symptom_logs.csv             # Symptom tracking logs (auto-created)
│   ├── policy_config.json           # Business rules and policies
│   ├── symptom_codes.csv            # SNOMED symptom code mappings
│   ├── drug_knowledge.csv           # Medication knowledge base
│   └── generated_qna_examples.json   # Generated Q&A examples
│
├── logs/                           # Runtime logs directory
│   ├── .gitkeep
│   ├── appointment_agent_log.jsonl  # Appointment interactions
│   ├── followup_agent_log.jsonl     # Symptom monitoring logs
│   ├── med_agent_log.jsonl          # Medication query logs
│   ├── caregiver_summaries.jsonl    # Caregiver summaries (JSON)
│   ├── caregiver_summaries.txt       # Caregiver summaries (Text)
│   └── orchestration_log.jsonl      # Routing and orchestration logs
│
├── evaluation/                     # Evaluation scripts and results
    ├── evaluate_langgraph.py        # LangGraph-specific evaluation
    ├── evaluate_agents.py           # Original evaluation script
    ├── benchmark_performance.py     # Performance benchmarking
    ├── generate_report.py           # HTML report generation
    ├── test_dataset.json            # Test dataset
    ├── results/                     # Evaluation results
    └── README.md                    # Evaluation documentation
└── prototype_demo/                  # Streamlit web UI demo
    ├── streamlit_app.py             # Streamlit interface
    └── README.md                    # Demo documentation
```

## 🚀 Quick Start

### 1. Setup (Standalone)

This package can be moved anywhere and run independently:

```bash
# Option 1: Use existing .venv (if copied from parent)
cd VoiceAgents/VoiceAgents_langgraph
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Option 2: Create new virtual environment
cd VoiceAgents_langgraph
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# If .env doesn't exist, copy from template
cp .env.example .env

# Edit .env with your API keys:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here  # Optional
# GOOGLE_API_KEY=your_key_here     # Optional
```

### 4. Run

**From inside VoiceAgents_langgraph/ directory (Recommended)**
```bash
cd VoiceAgents_langgraph
python main.py
```

**Alternative: From parent directory**
```bash
cd VoiceAgents  # parent directory
python -m VoiceAgents_langgraph.main
```

The `main.py` script automatically detects when run from inside the directory and adjusts Python paths accordingly.

## 📖 Usage

### CLI Commands

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

## 🏗️ Architecture

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

**nodes/appointment.py** ✅ **STT/TTS**: Handles appointment operations including status checks, rescheduling, cancellation, and new scheduling. Implements comprehensive triage logic (RED/ORANGE/GREEN) based on symptoms and enforces business rules (minor consent, referral requirements, telehealth policies, post-op windows).

**nodes/followup.py** ✅ **STT/TTS**: Logs patient-reported symptoms with severity scores. Uses LLM-powered symptom extraction with keyword fallback. Implements triage system (RED/ORANGE/GREEN) to flag serious symptoms. All interactions logged to `logs/followup_agent_log.jsonl`.

**nodes/medication.py** ✅ **STT/TTS**: Answers medication questions including side effects, missed dose advice, drug interactions, food guidance, and contraindications. Assesses risk levels (RED/ORANGE/GREEN). All interactions logged to `logs/med_agent_log.jsonl`.

**nodes/caregiver.py** ✅ **STT/TTS**: Generates weekly caregiver summaries by aggregating symptom trends and medication adherence data. Only processes summaries for patients with linked caregivers and consent on file. Logs to `logs/caregiver_summaries.jsonl` and `.txt`.

**nodes/help.py** ✅ **STT/TTS**: Provides general LLM-powered conversation for greetings, questions, and non-specific requests. Falls back to static help message if LLM unavailable.

## 📋 Triage System

The system implements a three-tier triage system for symptom assessment:

### RED Flags (Emergency)
- Chest pain, chest tightness, pain in chest
- Shortness of breath, trouble breathing
- Wound complications (opening, drainage, infection signs)
- High fever (>= 101.5°F)
- Severe pain (>= 8/10)
- Neurological deficits (numbness, weakness, slurred speech)
- Syncope (fainting)

**Response**: Directs patient to emergency department immediately, alerts healthcare provider

### ORANGE Flags (Concerning)
- Moderate pain (5-7/10)
- Low-grade fever (99.5-101.4°F)
- Dizziness
- Hyperglycemia (blood sugar > 300)
- Wound redness/swelling

**Response**: Nurse callback scheduled, tentative appointment hold available

### GREEN Flags (Normal)
Routine symptoms without immediate concern.

**Response**: Logged for provider review during next appointment

## 📝 Logging

All conversation flows are logged to the `logs/` directory:

- **appointment_agent_log.jsonl** - Appointment interactions (scheduling, rescheduling, triage)
- **followup_agent_log.jsonl** - Symptom reports with triage tier (RED/ORANGE/GREEN)
- **med_agent_log.jsonl** - Medication queries with risk assessment
- **caregiver_summaries.jsonl** - Caregiver summaries in JSON format
- **caregiver_summaries.txt** - Caregiver summaries in human-readable text
- **orchestration_log.jsonl** - All routing decisions and workflow invocations

Each log entry includes:
- Timestamp
- Agent name
- Patient ID
- User input
- Parsed data / intent
- Agent response
- Triage tier / risk level (where applicable)

## 🔧 Configuration

### Environment Variables (.env)

```bash
# LLM Provider (default: openai)
LLM_PROVIDER=openai          # Options: openai, anthropic, google

# OpenAI Configuration
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini

# Anthropic Configuration (optional)
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Google Configuration (optional)
GOOGLE_API_KEY=your_key_here
GOOGLE_MODEL=gemini-pro
```

### Switching LLM Providers

Edit `.env` and change `LLM_PROVIDER`:
```bash
LLM_PROVIDER=anthropic  # Use Claude
# or
LLM_PROVIDER=google     # Use Gemini
```

No code changes required!

## 🧪 Evaluation

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

## 🚢 Independence & Portability

This package is **fully independent** and can be moved anywhere:

### Moving the Package

```bash
# Copy to new location
cp -r VoiceAgents_langgraph /path/to/new/location/

# Or move
mv VoiceAgents_langgraph /path/to/new/location/

# From new location:
cd /path/to/new/location/VoiceAgents_langgraph
source .venv/bin/activate  # or create new venv
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python -m VoiceAgents_langgraph.main
```

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

## 💻 Programmatic Usage

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

## 🐛 Troubleshooting

### Issue: "No module named 'VoiceAgents_langgraph'"

**Solution**: Always run `main.py` directly from inside the `VoiceAgents_langgraph/` directory:
```bash
cd VoiceAgents_langgraph
python main.py
```

The `main.py` script automatically handles path adjustments. If you encounter this error, it means you're trying to use `python -m` from inside the directory - just use `python main.py` instead.

### Issue: "No module named 'langgraph'"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "OPENAI_API_KEY not found"

**Solution**: Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Issue: TTS/STT not working

**Solution**: Ensure required libraries are installed:
```bash
pip install pyttsx3 speechrecognition pyaudio
```

On macOS, you may need to install PortAudio:
```bash
brew install portaudio
```

### Issue: Logs directory not found

**Solution**: The `logs/` directory is auto-created. If issues persist, check write permissions:
```bash
mkdir -p logs
chmod 755 logs
```

## 📚 Additional Resources

- **Evaluation**: See `evaluation/README.md` for evaluation documentation
- **Original Implementation**: See parent `VoiceAgents/` directory for original implementation
- **Function Comparison**: See `FUNCTION_COMPARISON.md` in parent directory for detailed comparison

## ✅ Feature Checklist

- ✅ All core agent functions preserved
- ✅ STT support via audio files and microphone
- ✅ TTS support in all agent nodes
- ✅ Comprehensive logging to `logs/` directory
- ✅ Multi-provider LLM support
- ✅ Standalone independence
- ✅ Virtual environment included
- ✅ Environment configuration included
- ✅ Evaluation scripts included
- ✅ All data files self-contained

## 📄 License

Part of the CMU x Zyter Capstone Project.
