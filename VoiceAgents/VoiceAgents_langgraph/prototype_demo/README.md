# VoiceAgents LangGraph – Prototype Demo

This demo provides a **Streamlit interface** for interacting with the **LangGraph VoiceAgents** system, which uses a graph-based workflow to coordinate between specialized healthcare agents:

- **Appointment Agent** – scheduling, rescheduling, and status checking with triage
- **Follow-Up Agent** – symptom tracking and triage (RED/ORANGE/GREEN)
- **Medication Agent** – education, missed doses, and side-effects
- **Caregiver Agent** – caregiver summaries for dependent patients
- **Help Agent** – general conversation and help

The system uses LangGraph's StateGraph for workflow management, with an **LLM (GPT-4o-mini/Claude/Gemini)** for intent detection and **rule-based fallbacks** for robustness.

---

## 1. Environment Setup

### Requirements
- **Python 3.10+**
- Virtual environment recommended
- OpenAI/Anthropic/Google API key (optional for LLM features)

### Create Virtual Environment

From the `VoiceAgents_langgraph/` directory:

```bash
cd VoiceAgents_langgraph
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

Note: Ensure `streamlit` is installed (included in requirements.txt).

### Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here  # Optional
# GOOGLE_API_KEY=your_key_here     # Optional
```

---

## 2. Launching the Demo

Run Streamlit from the **VoiceAgents_langgraph/** directory:

```bash
cd VoiceAgents_langgraph

# Activate virtual environment (if not already active)
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Launch Streamlit
streamlit run prototype_demo/streamlit_app.py
```

Then open the link displayed in your terminal, usually:

```
http://localhost:8501
```

---

## 3. Interface Guide

### **Sidebar Settings**

* **Patient ID** – set your 8‑digit patient ID used by agents
* **Enable TTS** – toggle text‑to‑speech (local `pyttsx3`)
* **Logs** – optional orchestration logs viewer (count is configurable)

### **Conversation**

Displays chat history with metadata. Assistant messages show detected `intent` and `patient_id`.

### **Your Message**

Single compose panel with three controls of the same size/color (blue):

* **Record** – toggles Start/Stop recording. While recording, a red indicator is shown. After Stop, your speech is auto‑transcribed and loaded into the input box for editing.
* **Clear** – clears the input box.
* **Send** – sends the message to the LangGraph workflow.

Notes:
* You can edit the transcript before sending.
* File uploads are supported indirectly: drag a short audio to your OS, then use the mic if you need live capture. The underlying STT logic is shared.

### **Recent Orchestration Logs**

Displays the last N conversation turns saved to:

```
VoiceAgents_langgraph/logs/orchestration_log.jsonl
```

---

## 4. Example Conversations

### Appointment Inquiry

```
You: I am patient 10004235, can you check my appointment?
Agent: Great! I can confirm that your Follow-up - Cardiology with Dr. Johnson on October 08 at 02:20 PM is scheduled and confirmed.
Intent: appointment
Patient ID: 10004235
```

### Symptom Update with Triage

```
You: I've been feeling some tightness in my chest
Agent: I understand you're experiencing chest tightness. this could be a serious symptom. Please go to the nearest emergency department immediately...
Intent: followup
Patient ID: 10004235
```

### Medication Question

```
You: What are the side effects of metformin?
Agent: Metformin: Common side effects include nausea, diarrhea, stomach upset...
Intent: medication
Patient ID: 10004235
```

### Caregiver Summary

```
You: Give me the caregiver update for patient 10001217
Agent: Caregiver Update for Cara Wong (Mother: Wong, Parent)
       - Cara Wong reported no major symptoms in the last 7 days...
Intent: caregiver
Patient ID: 10001217
```

---

## 5. Speech‑to‑Text (STT)

The demo uses a robust cascade implemented in `utils/__init__.py::stt_transcribe`:

1) Local `faster-whisper` if installed (fast, no quota)
2) OpenAI Whisper API via `utils/llm_provider.py` (if `OPENAI_API_KEY` present)
3) `SpeechRecognition` Google backend

This ensures voice works even when OpenAI quota is exhausted.

Recording is explicit Start/Stop (no auto timeout). Raw chunks are buffered while recording, written to WAV on Stop, then transcribed using the cascade above.

---

## 6. Troubleshooting

| Problem | Likely Cause | Fix |
|---------|--------------|-----|
| `ModuleNotFoundError: No module named 'VoiceAgents_langgraph'` | Running from wrong directory | Run Streamlit from `VoiceAgents_langgraph/` directory |
| LLM features not working | No API key in `.env` | Create `.env` from `.env.example` and add your API keys |
| No sound from TTS | `pyttsx3` audio backend not configured | Ensure a local voice engine is installed |
| STT (mic) fails or no transcript | Missing `pyaudio`/PortAudio or mic permissions | `brew install portaudio && pip install pyaudio`; grant Terminal microphone permission |
| STT (OpenAI) returns empty | Quota exhausted or API error | The app falls back automatically; ensure `.env` if you want Whisper API |
| Local faster‑whisper slow | No GPU or float16 not supported | It automatically runs in float32; consider smaller model or CPU‑only |
| SSL error (OSStatus -26276) during pip | macOS certs not installed for Python | Run the system Python cert install script for your Python version |
| Streamlit not found | Missing streamlit package | Install: `pip install streamlit` or `pip install -r requirements.txt` |

---

## 7. Project Structure

```
VoiceAgents_langgraph/
├── prototype_demo/
│   ├── streamlit_app.py    # Streamlit UI
│   └── README.md           # This file
├── nodes/                   # LangGraph agent nodes
│   ├── routing.py          # Intent detection
│   ├── appointment.py      # Appointment management
│   ├── followup.py         # Symptom monitoring
│   ├── medication.py       # Medication Q&A
│   └── caregiver.py        # Caregiver summaries
├── utils/                   # Utilities (STT/TTS, LLM, logging)
├── data/                    # Data files (CSV, JSON)
├── logs/                    # Runtime logs
├── .env                     # Environment variables (create from .env.example)
└── requirements.txt         # Dependencies
```

---

## 8. Log Example

Each orchestration decision is recorded as one JSON line in `logs/orchestration_log.jsonl`:

```json
{
  "ts": "2025-10-29T20:36:40Z",
  "agent": "OrchestrationAgent",
  "intent": "appointment",
  "patient_id": "10004235",
  "input": "I am patient 10004235, can you check my appointment?",
  "routed_reply": "Great! I can confirm that your Follow-up - Cardiology...",
  "log_entry": { ... }
}
```

---

## 9. Notes

* Use **Python 3.10+** for consistent library compatibility
* Always launch Streamlit from the `VoiceAgents_langgraph/` directory
* LLM routing supports OpenAI, Anthropic, and Google - configure in `.env`
* When API key is absent, rule-based router ensures deterministic behavior
* All conversation flows are logged to `logs/` directory
* TTS/STT support throughout all agent nodes

---

**Author:** CMU Capstone Team  
**Last Updated:** October 2025 (updated UI, explicit mic Start/Stop, unified STT cascade)
