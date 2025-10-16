# Appointment Scheduling Agent

This module is part of the **CMU x Zyter Capstone Project**.  
It implements an **Appointment Scheduling Agent** that helps patients manage their appointments safely and efficiently.

---

## 🔑 Core Logic

### 1. Understanding the Patient’s Request
The agent listens to the patient’s message and identifies:
- **Who** the patient is (their ID)  
- **What** they want (reschedule, cancel, check status, or book new)  
- **Why** they need it (symptoms, routine follow-up, schedule conflict)  
- **If a caregiver is involved** (e.g., a parent for minors)

### 2. Safety Check (Triage First)
Before changing any appointments, the agent asks: **“Is this safe, or do we need urgent care?”**

- **RED (Urgent)**  
  - Signs: chest pain, shortness of breath, incision opening, high fever ≥ 101.5°F, severe pain ≥ 8
  - Action: Tell patient to go to ER / alert nurse immediately. Do not schedule.  

- **ORANGE (Concerning)**  
  - Signs: low fever (99.5–101.4°F), swelling/redness, blood sugar > 300, dizziness, moderate pain 5–7  
  - Action: A nurse will call today. System can “hold” a slot temporarily.  

- **GREEN (Safe)**  
  - Routine scheduling, mild/no symptoms  
  - Action: Proceed with scheduling  

### 3. Rules Before Booking (Policy Gates)
If safe, the system checks:
- **Follow-up window** → e.g., post-surgery visits must be within 7–14 days  
- **Insurance** → some plans require referral/authorization  
- **Minors** → under 18 need caregiver consent  
- **Telehealth limits** → some visits must be in-person  

### 4. Scheduling Workflow
1. Check if the patient already has an appointment.  
2. Look at available time slots.  
3. If requested slot is unavailable, suggest up to 3 alternatives.  
4. Confirm cancellation, reschedule, or booking once rules are met.  

### 5. Q&A Generator (Testing the Logic)
- Command `gen` generates 20 sample patient questions.  
- Each is labeled as RED/ORANGE/GREEN.  
- Results are saved in files for client/professor review.  

👉 In short: **Listen → Check safety → Apply rules → Book or escalate → Test with examples.**

---

## 📂 Repo Layout

```text
appointment_agent/
├── README.md
├── requirements.txt
├── src/
│   └── appointment_agent_workflow.py
├── data/
│   ├── patients.csv
│   ├── appointments.csv
│   ├── caregivers.csv
│   ├── available_slots.csv
│   └── policy_config.json
└── docs/
    ├── workflow_diagram.png
    └── demo_log.md

```

## 📊 Example Data

### patients.csv
```csv
patient_id,name,dob,age,language,chronic_conditions,primary_caregiver_id
10004235,Alice Lee,2001-08-08,24,ENGLISH,None,
10000032,Bob Chen,1971-03-10,54,ENGLISH,Diabetes,
10001217,Cara Wong,2008-02-01,17,ENGLISH,None,C001
```
### appoitments.csv
```csv
appointment_id,patient_id,appointment_date,appointment_type,doctor,status,urgency,can_reschedule,plan_id
30409,10000032,2025-10-15 09:30:00,"Surgery - Cardiac Bypass","Dr. Smith",Scheduled,high,False,HMO_A
30220,10004235,2025-10-08 14:20:00,"Follow-up - Cardiology","Dr. Johnson",Scheduled,medium,True,PPO_A
30384,10001217,2025-09-28 11:00:00,"Consultation - Diabetes","Dr. Wilson",Scheduled,low,True,HMO_A
```
### caregivers.csv
```csv
caregiver_id,name,relationship,consent_on_file
C001,Wong Parent,Mother,True
```
### available_slots.csv
```csv
date,doctor,appointment_type,location,modality
2025-10-09 10:00:00,Dr. Johnson,Follow-up - Cardiology,Clinic A,in_person
2025-10-10 15:30:00,Dr. Johnson,Follow-up - Cardiology,Clinic A,in_person
2025-09-30 09:00:00,Dr. Wilson,Consultation - Diabetes,Clinic B,video
```
### policy_config.json
```json
{
  "postop_windows": {
    "Cardiac Bypass": [7, 14],
    "Valve Repair": [7, 14]
  },
  "telehealth_allowed": {
    "Follow-up - Cardiology": true,
    "Consultation - Diabetes": true,
    "Suture Removal": false
  },
  "referral_required_plans": ["HMO_A"],
  "red_flags": ["chest pain", "shortness of breath", "wound opening", "yellow drainage", "fever >= 101.5", "pain >= 8"],
  "orange_flags": ["moderate pain 5-7", "low fever 99.5-101.4", "blood sugar > 300", "wound redness", "dizziness"]
}
```
## How to Run
### Run demo
cd appointment_agent/demos
python appointment_agent_workflow.py

## Example Session
Multi-Agent Appointment System (LLM + Rules)
Type 'gen' to auto-generate 20 Q&A examples and evaluate.
Type 'quit' to exit.

Patient: I am patient 10004235, can you check my appointment?
Agent: Your Follow-up - Cardiology with Dr. Johnson on October 08 at 02:20 PM is confirmed.

Patient: I had surgery last week, now I have chest pain 8 out of 10 and trouble breathing
Agent: Your symptoms may be serious. Please go to the nearest emergency department now. I am alerting the on-call nurse.

Patient: I have low-grade fever 100.8 and some swelling after surgery
Agent: I will have a nurse call you today to review your symptoms. I can place a tentative hold for a visit in the next 24–48 hours.

Patient: I am patient 10001217, can I reschedule my appointment to October 9?
Agent: I can offer these times: October 09 at 10:00 AM (Clinic A, in_person), October 10 at 03:30 PM (Clinic A, in_person). Which works best?

## Notes:
### API Key

Required if you want LLM parsing and Q&A generation (OPENAI_API_KEY).

If no key is set, the workflow still runs in rule-based mode.

```text
export OPENAI_API_KEY=sk-xxxx   # Mac/Linux
setx OPENAI_API_KEY "sk-xxxx"   # Windows
```
