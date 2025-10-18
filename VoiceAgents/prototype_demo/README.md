Here’s a complete **README.md** you can place in
`VoiceAgents/prototype_demo/README.md`
It’s written purely as a **user instruction guide** and assumes **Python 3.10**.

---

````markdown
# VoiceAgents Orchestrator – Prototype Demo

This demo provides a **Streamlit interface** for interacting with the multi-agent **VoiceAgents Orchestrator**, which coordinates between four specialized agents:

- **Appointment Agent** – scheduling, rescheduling, and status checking  
- **Follow-Up Agent** – symptom tracking and triage  
- **Medication Agent** – education, missed doses, and side-effects  
- **Caregiver Agent** – caregiver summaries for dependent patients  

The orchestrator decides which agent should handle each user message, using an **LLM (GPT-4o-mini)** for intent detection and **rule-based fallbacks** for robustness.

---

## 1. Environment Setup

### Requirements
- **Python 3.10**
- Conda or virtual environment recommended
- OpenAI API key (optional for LLM features)

### Create a new environment
```bash
conda create -n voiceagents_env python=3.10
conda activate voiceagents_env
````

### Install dependencies

From the `VoiceAgents` project root:

```bash
pip install -r requirements.txt
```

---

## 2. Launching the Demo

Run Streamlit from the **project root**, not from inside the demo folder:

```bash
cd /.../Capstone_KG_VoiceAgents/VoiceAgents
conda activate voiceagents_env
export OPENAI_API_KEY=sk-xxxx            # optional
streamlit run prototype_demo/streamlit_app.py
```

Then open the link displayed in your terminal, usually:

```
http://localhost:8501
```

---

## 3. Interface Guide

### **Sidebar Settings**

* **Default Patient ID** – set or change your 8-digit patient ID
* **Enable TTS** – toggle text-to-speech (depends on local `pyttsx3` audio)
* **Show Recent Logs** – display orchestration routing logs

### **Main Chat Window**

* Type or paste your message (for example, “I am patient 10004235, can you check my appointment?”).
* Each response shows:

  * **Agent Reply**
  * **Detected Intent**
  * **Patient ID**
  * The routed sub-agent’s output

### **Recent Orchestration Logs**

Displays the last N conversation turns saved to:

```
orchestration_agent/demos/logs/orchestration_log.jsonl
```

---

## 4. Example Conversations

### Appointment Inquiry

```
You: I am patient 10004235, can you check my appointment?
Agent: Your follow-up with Dr. Johnson on October 08 at 02:20 PM is confirmed.
```

### Symptom Update

```
You: I feel dizzy and my glucose was 320 yesterday.
Agent: I've recorded your symptom dizziness and glucose reading for review at your next appointment.
```

### Caregiver Summary

```
You: My child is 17 and needs a caregiver summary for this week.
Agent: Caregiver Update for Alice Lee (Mother: Wong Parent) – dizziness 3×, shortness of breath 2×. Overall risk: LOW.
```

### Medication Check

```
You: Can you summarize medication changes for Bob Chen?
Agent: Metformin dosage unchanged. Continue current regimen. Last refill: October 12.
```

### Help / Fallback

```
You: quit
Agent: I can help with appointments, symptoms (follow-up), medications, and caregiver summaries.
       Try something like:
       - "I am patient 10004235, check my appointment"
       - "I feel dizzy 7/10"
       - "What are the side effects of metformin?"
       - "Give me this week’s caregiver update for 10001217"
```

---

## 5. Troubleshooting

| Problem                                              | Likely Cause                            | Fix                                              |
| ---------------------------------------------------- | --------------------------------------- | ------------------------------------------------ |
| `ModuleNotFoundError: No module named 'common_data'` | Running from inside sub-folder          | Run Streamlit from the **VoiceAgents** root      |
| LLM features not working                             | No `OPENAI_API_KEY` set                 | Run `export OPENAI_API_KEY=sk-xxxx`              |
| No sound from TTS                                    | `pyttsx3` audio backend not configured  | Ensure a local voice engine is installed         |
| STT (speech-to-text) fails                           | Missing `SpeechRecognition` / `pyaudio` | Install: `pip install SpeechRecognition pyaudio` |

---

## 6. Project Structure

```
VoiceAgents/
├── appointment_agent/
│   ├── demos/
│   │   ├── __pycache__/
│   │   └── appointment_agent_workflow.py
│   ├── qna_examples/
│   │   ├── generated_qna_examples.csv
│   │   └── generated_qna_examples.json
│   └── README.md
│
├── caregiver_agent/
│   ├── demos/
│   │   ├── __pycache__/
│   │   └── caregiver_agent_workflow.py
│   ├── logs/
│   │   ├── caregiver_summaries.jsonl
│   │   └── caregiver_summaries.txt
│   └── README.md
│
├── common_data/
│   ├── __pycache__/
│   ├── data/
│   │   ├── appointments.csv
│   │   ├── caregivers.csv
│   │   ├── patients.csv
│   │   ├── prescriptions.csv
│   │   └── symptom_logs.csv
│   ├── database.py
│   └── policy_config.json
│
├── followup_agent/
│   ├── demos/
│   │   ├── __pycache__/
│   │   └── followup_agent_workflow.py
│   ├── logs/
│   │   └── followup_agent_log.jsonl
│   ├── symptom_codes.csv
│   └── README.md
│
├── medication_agent/
│   ├── demos/
│   │   ├── __pycache__/
│   │   └── medication_agent_workflow.py
│   ├── logs/
│   │   └── med_agent_log.jsonl
│   ├── drug_knowledge.csv
│   └── README.md
│
├── orchestration_agent/
│   ├── demos/
│   │   ├── __pycache__/
│   │   └── orchestration_agent_workflow.py
│   ├── logs/
│   │   └── orchestration_log.jsonl
│   └── README.md
│
├── prototype_demo/
│   ├── streamlit_app.py
│   ├── README.md
│   └── requirements.txt
│
└── .mypy_cache/

```

---

## 7. Log Example

Each orchestration decision is recorded as one JSON line:

```json
{
  "ts": "2025-10-18T05:36:40Z",
  "agent": "OrchestrationAgent",
  "intent": "appointment",
  "patient_id": "10004235",
  "input": "I am patient 10004235, can you check my appointment?",
  "routed_reply": "Your follow-up with Dr. Johnson on October 08 at 02:20 PM is confirmed."
}
```

---

## 8. Notes

* Use **Python 3.10** for consistent library compatibility.
* Always launch Streamlit from the project root to preserve relative imports.
* LLM routing uses GPT-4o-mini; when the API key is absent, a rule-based router ensures deterministic behavior.
* You can safely extend this demo with additional agents (e.g., billing or nutrition) by registering new intent handlers inside the orchestration layer.

---

**Author:** CMU Capstone Team
**Last Updated:** October 2025

```

---

This version is polished for user distribution—clear, single-source instructions with no internal development notes. It’s ready to include directly in your repository.
```
