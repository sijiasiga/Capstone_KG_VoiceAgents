# Assignment: Multi-Agent Voice Orchestration for Hospital Discharge & Post-Care Follow-Up

## Background

Patients discharged after major illnesses (like heart failure, COPD, or diabetes complications) face high risk of readmission. The main reasons are:
• Patients don’t follow medication instructions properly.
• They miss follow-up appointments.
• They don’t report early symptoms until it’s too late.
• Caregivers often remain uninformed.

A multi-agent voice system can simulate how healthcare organizations improve compliance by orchestrating multiple specialized voice agents.

This assignment will give you practice in:
• Conversational design.
• Multi-agent orchestration logic.
• Representing medical rules as computable flows.
• Working with healthcare mock data.

---

## Use Case Summary

A Primary Voice Agent (PVA) handles patient conversations and delegates to 3 specialized agents. This can be done as a mobile app or as a web app for this project (Based on convenience of the required skill):

### 1. Medication Education Agent

• Explains prescriptions in simple language.
• Logs adherence.
• Checks drug schedule overlaps.

### 2. Follow-Up & Monitoring Agent

• Handles daily symptom check-ins.
• Tracks appointment adherence.
• Flags red alerts for clinical review.

### 3. Caregiver Communication Agent

• Summarizes patient status for a caregiver.
• Sends alerts for non-adherence or risk symptoms.

The Orchestration Layer (OVA) coordinates all three, deciding which agent to invoke and aggregating results.

---

## Data Sources

Students will not connect to live EHRs (protected). Instead, use:
• Mock Datasets (provided or public or can be synthetic):
o MIMIC-III (de-identified ICU dataset from MIT).
o CMS Chronic Condition Data Warehouse (sample records).
• Synthetic Discharge Data: Instructor can give CSV/JSON files with fields:
o patient_id, medication_name, dosage, schedule, discharge_date, caregiver_contact, appointment_date
• Symptom Logs: Students can simulate patient daily input:
o “I feel fine”, “I have swelling in my legs”, “I missed 2 pills yesterday.”

---

## Input/Output Flow by Agent

### 1. Medication Education Agent

**Input:**
o Medication list (from synthetic dataset).
o Patient query: natural language (“Do I take the blue pill tonight?”).

**Processing:**
o Parse query → identify drug name.
o Check schedule in dataset.
o Detect adherence gaps.

**Output:**
o Patient-facing answer: “Yes, you must take 1 tablet of Metoprolol at 9 PM.”
o Structured log: `{patient_id: 101, med: Metoprolol, status: Taken, time: 9 PM}`

---

### 2. Follow-Up & Monitoring Agent

**Input:**
o Patient symptom report (“I feel breathless today”).
o Appointment data (next visit date).

**Processing:**
o Map symptom → medical code (SNOMED: shortness_of_breath).
o Apply rule: If symptom is severe OR repeats ≥ 2 times in a week → flag red alert.

**Output:**
o Patient reassurance: “I’ve logged your symptom. Since it occurred twice this week, I’ll notify your provider.”
o Structured log: `{patient_id: 101, symptom: breathlessness, severity: moderate, alert: true}`

---

### 3. Caregiver Communication Agent

**Input:**
o Logs from Medication + Follow-Up agents.

**Processing:**
o Summarizes adherence and symptoms.
o Generates alerts for non-adherence.

**Output:**
o Caregiver update message:
“Patient missed 2 doses this week and reported breathlessness twice. Please check on them.”
o Structured alert: `{caregiver_id: C123, patient_id: 101, risk_level: HIGH}`

---

### 4. Orchestration Agent (OVA)

**Input:**
o Raw patient conversation.

**Processing:**
o Detect intent (medication vs. symptom vs. caregiver question).
o Route to appropriate specialized agent.
o Aggregate multi-agent results into single conversation flow.

**Output:**
o Unified conversation with patient.
o Audit log of which agent handled what.

---

## Tasks

### Task A: Build Data Models

• Define tables/files: patients, medications, appointments, symptoms, caregivers.
• Populate with at least 15-20 synthetic records.

### Task B: Orchestration Flow Design

• Draw intent → agent → output mapping.
• Define escalation rules (when to involve caregiver agent).

### Task C: Sample Dialogues

• At least 3 conversations per agent.
**Example:**
Patient: “I forgot my water pill yesterday.”
PVA → Medication Agent → Output: “Please take it as scheduled tonight. I’ll record yesterday as missed.”

### Task D: Computable Criteria

• Encode at least 3 rules, e.g.:
o IF missed_doses ≥ 2 in 1 week → alert caregiver.
o IF symptom == breathlessness ≥ 2 times → flag provider.

---

## Evaluation Criteria

• Completeness: Did you cover all three agents + orchestration and ?
• Accuracy: Do flows align with realistic discharge & follow-up needs?
• Clarity: Are input/output mappings well-documented?
• Creativity: Extra features (multilingual responses, sentiment detection, visualization of alerts).
• Transparency:
• Can reviewers see the patient-agent conversation logs (input + output)?
• Is there a human review dashboard where caregivers can validate the agent’s responses?
• Does the system make it clear why a certain decision (e.g., escalation) was made?

---

Would you like me to make a downloadable `.md` file version (so you can add it directly to your GitHub repo as `README.md`)?
