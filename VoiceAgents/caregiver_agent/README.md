# Caregiver Communication Agent

This module is part of the **CMU × Zyter Capstone Project**.  
It implements a **Caregiver Communication Agent** that automatically summarizes a patient's weekly activity — including symptoms, medication adherence, and upcoming appointments — and generates structured and natural-language updates for caregivers with consent on file.

---

## 🔑 Core Logic

### 1. Purpose
The agent acts as a "weekly health assistant" for patients who have a caregiver.  
It aggregates data from all other agents and produces concise summaries such as:

> "This week Cara reported dizziness twice (average severity 6) and missed one medication dose. No urgent symptoms detected. Next appointment: Oct 25 with Dr. Wilson."

---

### 2. Inputs

| Data Type | Source | Description |
|-----------|--------|-------------|
| **Patient info** | `patients.csv` | Demographics and caregiver link |
| **Caregiver info** | `caregivers.csv` | Name, relationship, consent flag |
| **Symptom logs** | `common_data/data/symptom_logs.csv` | From Follow-Up Agent |
| **Medication logs** | `med_agent_log.jsonl` or `med_logs.csv` | From Medication Agent |
| **Appointments** | `appointments.csv` | Shared across agents |

---

### 3. Workflow
```
1️⃣ Identify patients with caregiver consent
2️⃣ Load past 7 days of symptom + medication + appointment data
3️⃣ Aggregate:
     • frequency and average severity of symptoms
     • count of missed/taken medications
4️⃣ Score risk:
     • severe/repeated symptoms + non-adherence → HIGH
     • repeated symptoms or some non-adherence → MODERATE
     • none → LOW
5️⃣ Generate caregiver summary (text + structured JSON)
6️⃣ Save to logs and optionally speak aloud (TTS)
```

---

## 📂 Repo Layout
```
caregiver_agent/
├── README.md
├── demos/
│   ├── caregiver_agent_workflow.py
│   └── logs/
│       ├── caregiver_summaries.jsonl
│       └── caregiver_summaries.txt
└── relies on shared data:
    └── ../common_data/data/
```

## 📊 Example Data

### patients.csv
```csv
patient_id,name,dob,age,language,chronic_conditions,primary_caregiver_id
10004235,Alice Lee,2001-08-08,24,ENGLISH,None,
10000032,Bob Chen,1971-03-10,54,ENGLISH,Diabetes,
10001217,Cara Wong,2008-02-01,17,ENGLISH,None,C001
```

### caregivers.csv
```csv
caregiver_id,name,relationship,consent_on_file
C001,Wong Parent,Mother,True
```

### symptom_logs.csv
```csv
ts_iso,patient_id,symptom,severity,note
2025-10-16T03:21:45Z,10001217,dizziness,6,"Feeling dizzy again 6/10"
2025-10-13T09:15:10Z,10001217,dizziness,5,"Morning dizziness"
```

### med_agent_log.jsonl
```json
{"ts": "2025-10-14T08:00:00Z", "patient_id": "10001217", "med": "Lasix", "status": "taken"}
{"ts": "2025-10-15T08:00:00Z", "patient_id": "10001217", "med": "Lasix", "status": "missed"}
```

## ⚙️ How to Run

From the VoiceAgents directory:
```bash
cd VoiceAgents
python -m caregiver_agent.demos.caregiver_agent_workflow
```

### Commands inside the CLI
```
:voice on | :voice off     → toggle text-to-speech
pid <8digit>               → set patient ID context
one                        → summarize this patient (7 days)
weekly                     → summarize all patients with caregiver consent
:stt <path.wav>            → optional speech-to-text demo
quit                       → exit
```

## 🧠 Workflow Summary

| Stage | Component | Description |
|-------|-----------|-------------|
| Input | Shared CSV + JSONL data | Patient, caregiver, symptom, medication, appointment |
| Aggregation | Rule engine | Weekly symptom + medication analysis |
| Risk Scoring | Heuristic | HIGH / MODERATE / LOW |
| Output | Text + JSONL + TTS | Caregiver-friendly summary |
| Logging | caregiver_summaries.* | Structured history for analytics |

## 📄 Example Output

### JSON (log)
```json
{
  "ts": "2025-10-16T03:21:45Z",
  "agent": "CaregiverCommunicationAgent",
  "patient_id": "10001217",
  "patient_name": "Cara Wong",
  "caregiver_id": "C001",
  "caregiver_name": "Wong Parent",
  "risk_level": "Moderate",
  "risk_rationale": "Repeated symptoms or some non-adherence.",
  "symptoms": {
    "count": 2,
    "avg_severity": 5.5,
    "flags": ["repeated dizziness (2×)"]
  },
  "medication": {
    "taken": 1,
    "missed": 1,
    "flags": []
  },
  "appointment_line": "Next appointment: October 25 at 02:20 PM with Dr. Wilson.",
  "summary_text": "Caregiver Update for Cara Wong (Mother: Wong Parent)\n• Symptoms reported 2× (avg 5.5/10); repeated dizziness.\n• Medication taken 1, missed 1.\n• Next appointment: October 25 at 2:20 PM with Dr. Wilson.\n• Risk level: Moderate."
}
```

### Text (summary)
```
Caregiver Update for Cara Wong (Mother: Wong Parent)
- Symptoms reported 2× (avg 5.5/10); repeated dizziness.
- Medication taken 1, missed 1.
- Next appointment: October 25 at 2:20 PM with Dr. Wilson.
- Risk level this week: Moderate.
Recommendation: Please check in with the patient if risk is Moderate or High.
```

## 🧩 Integration Notes

- Consumes logs from Follow-Up and Medication agents
- Shares `DatabaseService` with all agents for unified data access
- Outputs can be read by Orchestration Agent or displayed in Caregiver Dashboard
- Provides both JSON (for systems) and natural text (for human review)
- Only processes patients with caregiver consent on file