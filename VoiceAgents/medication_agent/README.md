# 💊 Medication Education Agent

This module is part of the **CMU x Zyter Capstone Project**.  
It implements a **Medication Education Agent** that helps patients understand their prescriptions, manage medication adherence, and recognize possible side effects or drug interactions using both **LLM** and **rule-based reasoning**.

---

## 🔑 Core Logic

### 1. Understanding the Patient’s Question
The agent listens to the patient’s message — either text or speech — and identifies:
- **Who** the patient is (via patient ID)
- **Which medication** they are referring to
- **What kind of question** they are asking (side effect, missed dose, interaction, etc.)

LLM-based parsing (`gpt-4o-mini`) or rule-based fallback classifies the intent into one of:
- `side_effect`
- `missed_dose`
- `interaction_check`
- `instruction`
- `contraindication`
- `general`

---

### 2. Accessing Patient & Prescription Data
Using a shared **DatabaseService** (from `common_data/database.py`), the agent retrieves:
- Patient demographics and chronic conditions
- Active prescriptions (e.g., Metformin, Furosemide, Aspirin)
- Linked drug knowledge base (`drug_knowledge.csv`)

This ensures every response is **personalized** to the patient’s current medications.

---

### 3. Knowledge Retrieval
The agent matches patient prescriptions against the **drug knowledge base**, which contains:
- Common side effects  
- Serious drug interactions  
- Missed dose instructions  
- Food and alcohol warnings  
- Contraindications and dosage adjustments  

Each field is stored in `drug_knowledge.csv` for structured retrieval.

---

### 4. Risk Assessment (LLM + Rules)
The agent performs a **risk-level assessment** for safety:

| Level | Trigger | Example | Action |
|--------|----------|----------|----------|
| **RED (High)** | Double-dosing, contraindication, dangerous interactions | “I took two insulin shots.” | Urge emergency evaluation |
| **ORANGE (Moderate)** | Missed dose, mild side effects | “I forgot my metformin this morning.” | Advise contacting provider soon |
| **GREEN (Low)** | General information, routine questions | “Can I take this with food?” | Provide educational answer |

---

### 5. Output
The agent responds in both text (and optional **text-to-speech**) with:
- Patient-friendly explanation
- Safety notice (⚠️ prefix for RED/ORANGE)
- Structured JSON log for analytics

Each interaction is stored in:
```
VoiceAgents/medication_agent/demos/logs/med_agent_log.jsonl
```
Example log entry:
```json
{
  "ts": "2025-10-15T19:40:21Z",
  "agent": "MedicationEducationAgent",
  "patient_id": "10004235",
  "input": "I forgot to take my medicine",
  "intent": "missed_dose",
  "risk_level": "ORANGE",
  "response": "⚠️ Potential issue detected. Please contact your clinician soon. Metformin: Take as soon as you remember; skip if near the next dose."
}
```
## 🧠 Workflow Summary

👉 **Listen → Parse → Retrieve Knowledge → Assess Risk → Explain Safely → Log**

## 📁 Repo Layout

```text
medication_agent/
├── README.md
├── demos/
│   └── medication_agent_workflow.py
├── drug_knowledge.csv
└── logs/
    └── med_agent_log.jsonl
```

---

## 📊 Example Data

### drug_knowledge.csv

```csv
drug_name,drug_class,common_side_effects,serious_interactions,missed_dose_advice,food_advice,contraindications,pregnancy_warning,renal_adjustment,alcohol_warning
Metformin,Antidiabetic,"nausea, diarrhea, bloating","Avoid alcohol due to lactic acidosis risk","Take as soon as you remember; skip if near the next dose","Take with food","Severe renal impairment (eGFR < 30)","Use during pregnancy only if clearly needed","Reduce dose if eGFR < 45","Avoid alcohol completely"
Furosemide,Loop diuretic,"dizziness, dehydration, low potassium","Avoid other diuretics or NSAIDs","Take as soon as you remember unless the next dose is near","Take in the morning to avoid nighttime urination","Severe electrolyte depletion","Category C - weigh risk vs benefit","Adjust dose for renal impairment","Avoid alcohol (dehydration risk)"
Aspirin,Antiplatelet,"stomach upset, heartburn","Avoid warfarin or ibuprofen","Take as soon as you remember unless next dose is near","Take after food","Active peptic ulcer disease, bleeding disorders","Avoid during the last trimester","No adjustment needed","Avoid alcohol (bleeding risk)"
Insulin,Antidiabetic,"hypoglycemia, dizziness","Avoid skipping meals","If missed, check blood sugar and take next scheduled dose","Inject before meals","Hypoglycemia unawareness","Generally safe in pregnancy","Dose adjustment based on glucose monitoring","Avoid alcohol (may cause hypoglycemia)"
```

## 🚀 How to Run

### 1. Install Dependencies
```bash
pip install pandas pyttsx3 SpeechRecognition pyaudio openai
```
### 2. (Optional) Add OpenAI API Key
```bash
setx OPENAI_API_KEY "sk-xxxx"   # Windows
export OPENAI_API_KEY=sk-xxxx   # Mac/Linux
```
### 3. Run the Demo (from project root VoiceAgents)
```bash
python -m medication_agent.demos.medication_agent_workflow
```

## 💬 Example Session
```
Medication Education Agent (LLM + Rules + STT/TTS)
Commands:
:voice on | :voice off
:stt <path_to_audio.wav/mp3>
:mic on
pid <8digit>
quit
```

## 🧪 Example Interactions

### Case 1 – Missed Dose
```
Patient: I forgot to take my medicine
Agent: ⚠️ Potential issue detected. Please contact your clinician soon. Metformin: Take as soon as you remember; skip if near the next dose.
```

### Case 2 – Side Effects
```
Patient: What are the side effects of my medication?
Agent: Metformin: Common side effects include nausea, diarrhea, bloating.
```


### Case 3 – Interaction
```
Patient: Can I take aspirin with ibuprofen?
Agent: ⚠️ High-risk situation detected. Please seek immediate medical care. Aspirin: Avoid warfarin or ibuprofen.
```


---

## 🧩 Notes

- Works with both **voice** and **text** input  
- **LLM is optional** — rule-based fallback ensures offline reliability  
- Every interaction is logged in structured JSON for explainability  
- Designed to integrate with the **Orchestration Agent** for unified multi-agent coordination
