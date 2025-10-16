# Follow-Up & Monitoring Agent

This module is part of the **CMU × Zyter Capstone Project**.  
It implements an **intelligent symptom tracking agent** that listens to patient reports, maps them to clinical codes, evaluates safety, and alerts providers when necessary.

---

## 🔑 Core Logic

### 1. Understanding the Patient’s Report
The agent listens to a patient’s message or voice input and extracts:
- **Who** the patient is (their ID)  
- **What** symptom they report (e.g., “breathless”, “leg swelling”)  
- **How bad** it is (numeric severity 0–10)  
- **When** it occurred (logged with UTC timestamp)

It can accept input in three ways:
- Text typed into the console  
- A recorded audio file (`:stt path_to_audio.wav`)  
- Direct microphone capture (`:mic on`)

---

### 2. Mapping to Medical Terminology
The agent standardizes every symptom using **SNOMED CT codes** from a local codebook (`symptom_codes.csv`):

| Raw phrase | Canonical term | SNOMED code |
|-------------|----------------|--------------|
| shortness of breath | breathlessness | 267036007 |
| leg swelling | leg_swelling | 271809000 |
| chest pain | chest_pain | 29857009 |
| fever | fever | 386661006 |

If a phrase is missing from the CSV, the agent asks the **LLM** (OpenAI GPT-4o-mini) to infer a canonical term and placeholder SNOMED code.

---

### 3. Safety Evaluation (Rule-Based)
Each new symptom is logged in `common_data/data/symptom_logs.csv`.  
The agent then reviews the patient’s recent history (past 7 days) and applies the following triage rules:

| Rule | Tier | Action |
|------|------|--------|
| Severity ≥ 8 | **RED** | Urgent — notify provider immediately |
| Same symptom ≥ 2× in 7 days | **ORANGE** | Recurrent — flag provider notification |
| Otherwise | **GREEN** | Routine — log only |

---

### 4. Context Awareness
Before responding, the agent also checks for any **upcoming appointments** via the shared `DatabaseService`:

> “Your next appointment is October 25 at 2:20 PM with Dr. Johnson.”

This helps link symptom updates to the patient’s care plan.

---

### 5. Patient-Facing Response
Depending on triage tier, the agent provides both text and optional voice output:

- **RED**  
  > “I’ve logged your symptom (*breathlessness; SNOMED 267036007*). Because the severity is high, I’ll notify your provider now.”

- **ORANGE**  
  > “Since it occurred at least twice this week, I’ll notify your provider.”

- **GREEN**  
  > “Thanks for the update — no alert triggered at this time.”

---

### 6. Structured Logging
Every event is appended to  
`VoiceAgents/followup_agent/demos/logs/followup_agent_log.jsonl`  
for downstream analytics or caregiver alerts.

Example log entry:
```json
{
  "ts": "2025-10-16T03:21:45Z",
  "agent": "FollowUpMonitoringAgent",
  "patient_id": "10004235",
  "symptom": "breathlessness",
  "snomed": "267036007",
  "severity": 7,
  "alert": true,
  "tier": "ORANGE",
  "raw_text": "Feeling breathless again 7/10"
}

## 📂 Repo Layout
```
followup_agent/
├── README.md
├── symptom_codes.csv
├── demos/
│   ├── followup_agent_workflow.py
│   └── logs/
│       └── followup_agent_log.jsonl
└── relies on shared database:
    └── ../common_data/database.py
```

## 📊 Example Data

### symptom_codes.csv
```csv
term,snomed_code,canonical
shortness of breath,267036007,breathlessness
breathless,267036007,breathlessness
trouble breathing,267036007,breathlessness
leg swelling,271809000,leg_swelling
edema,271809000,leg_swelling
fever,386661006,fever
dizziness,404640003,dizziness
chest pain,29857009,chest_pain
cough,49727002,cough
fatigue,84229001,fatigue
```

### symptom_logs.csv (auto-generated)
```csv
ts_iso,patient_id,symptom,severity,note
2025-10-16T03:21:45Z,10004235,breathlessness,7,"Feeling breathless again 7/10"
```

## ⚙️ How to Run
```bash
cd VoiceAgents
python -m followup_agent.demos.followup_agent_workflow
```

### Commands inside the CLI:
```
:voice on | :voice off        # toggle text-to-speech
:stt <path_to_audio.wav>      # transcribe an audio file
:mic on                       # capture one spoken sentence
pid <8digit>                  # set patient_id
quit                          # exit
```

## 🧠 Workflow Summary
```
👉 Listen → Parse → Map to SNOMED → Evaluate Safety → Respond → Log
```

| Stage | Component | Description |
|-------|-----------|-------------|
| Input | Text, audio, or mic | Patient reports symptom |
| Parsing | LLM / heuristic | Extract symptom + severity |
| Normalization | Codebook / LLM | Map to SNOMED |
| Evaluation | Rule engine | Detect repeat or severe cases |
| Response | Text + optional TTS | Escalate or reassure |
| Logging | JSONL + CSV | Structured records for analytics |

## 🧩 Integration Notes

- Shares `DatabaseService` with Appointment and Medication agents
- Logs feed into the Caregiver Communication Agent for weekly summaries
- Fully modular: can run standalone or via the Orchestration Agent