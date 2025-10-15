
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import pandas as pd
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QNA_DIR = os.path.join(BASE_DIR, "qna_examples")  # stays inside demos/
os.makedirs(QNA_DIR, exist_ok=True)


# Optional: comment out pyttsx3 if not available in your env
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# Optional: if you don't have OpenAI client configured, set USE_LLM=False
USE_LLM = True
try:
    from openai import OpenAI
    client = OpenAI()
except Exception:
    USE_LLM = False
    client = None

# -----------------------------
# Mock Data & Policy Config
# -----------------------------

appointments_data = pd.DataFrame([
    {"appointment_id": 30409, "patient_id": "10000032", "appointment_date": "2025-10-15 09:30:00",
     "appointment_type": "Surgery - Cardiac Bypass", "doctor": "Dr. Smith", "status": "Scheduled",
     "urgency": "high", "can_reschedule": False, "plan_id": "HMO_A"},
    {"appointment_id": 30220, "patient_id": "10004235", "appointment_date": "2025-10-08 14:20:00",
     "appointment_type": "Follow-up - Cardiology", "doctor": "Dr. Johnson", "status": "Scheduled",
     "urgency": "medium", "can_reschedule": True, "plan_id": "PPO_A"},
    {"appointment_id": 30384, "patient_id": "10001217", "appointment_date": "2025-09-28 11:00:00",
     "appointment_type": "Consultation - Diabetes", "doctor": "Dr. Wilson", "status": "Scheduled",
     "urgency": "low", "can_reschedule": True, "plan_id": "HMO_A"}
])

available_slots = pd.DataFrame([
    {"date": "2025-10-09 10:00:00", "doctor": "Dr. Johnson", "appointment_type": "Follow-up - Cardiology", "location": "Clinic A", "modality": "in_person"},
    {"date": "2025-10-10 15:30:00", "doctor": "Dr. Johnson", "appointment_type": "Follow-up - Cardiology", "location": "Clinic A", "modality": "in_person"},
    {"date": "2025-09-30 09:00:00", "doctor": "Dr. Wilson", "appointment_type": "Consultation - Diabetes", "location": "Clinic B", "modality": "video"}
])

patients = pd.DataFrame([
    {"patient_id": "10004235", "name": "Alice Lee", "dob": "2001-08-08", "age": 24, "language": "ENGLISH", "chronic_conditions": ["None"], "primary_caregiver_id": None},
    {"patient_id": "10000032", "name": "Bob Chen", "dob": "1971-03-10", "age": 54, "language": "ENGLISH", "chronic_conditions": ["Diabetes"], "primary_caregiver_id": None},
    {"patient_id": "10001217", "name": "Cara Wong", "dob": "2008-02-01", "age": 17, "language": "ENGLISH", "chronic_conditions": ["None"], "primary_caregiver_id": "C001"}
])

caregivers = pd.DataFrame([
    {"caregiver_id": "C001", "name": "Wong, Parent", "relationship": "Mother", "consent_on_file": True}
])

# Policy-like config. Move to YAML/JSON if needed.
POLICY = {
    "postop_windows": {
        # days after surgery: min, max
        "Cardiac Bypass": (7, 14),
        "Valve Repair": (7, 14),
    },
    "telehealth_allowed": {
        "Follow-up - Cardiology": True,
        "Consultation - Diabetes": True,
        "Suture Removal": False,
    },
    "referral_required_plans": ["HMO_A"],
    "red_flags": [
        {"name": "chest_pain", "pattern": ["chest pain"], "threshold": None},
        {"name": "shortness_of_breath", "pattern": ["shortness of breath", "trouble breathing"], "threshold": None},
        {"name": "wound_dehiscence", "pattern": ["incision opening", "wound opening", "dehiscence", "yellow drainage", "pus"], "threshold": None},
        {"name": "fever_high", "pattern": ["fever"], "threshold": 101.5},
        {"name": "severe_pain", "pattern": ["pain"], "threshold": 8},
        {"name": "neuro_deficit", "pattern": ["numbness", "weakness", "slurred speech"], "threshold": None},
        {"name": "syncope", "pattern": ["fainted", "syncope"], "threshold": None},
    ],
    "orange_flags": [
        {"name": "moderate_pain", "pattern": ["pain"], "range": (5,7)},
        {"name": "fever_low", "pattern": ["fever"], "range": (99.5, 101.4)},
        {"name": "hyperglycemia", "pattern": ["glucose", "blood sugar"], "threshold": 300},
        {"name": "wound_redness", "pattern": ["redness", "swelling"], "threshold": None},
        {"name": "dizziness", "pattern": ["dizzy", "dizziness"], "threshold": None},
    ]
}

# -----------------------------
# Utilities
# -----------------------------

def say(text: str, speaker: str, use_voice: bool = False):
    print(f"\n{speaker}: {text}")
    if use_voice and pyttsx3 is not None:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', 150)
        engine.say(f"{speaker} says: {text}")
        engine.runAndWait()

def to_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def appt_summary(appt: pd.Series) -> str:
    dt = to_dt(appt["appointment_date"]).strftime("%B %d at %I:%M %p")
    return f"{appt['appointment_type']} with {appt['doctor']} on {dt}"

# -----------------------------
# LLM Helpers
# -----------------------------

def llm_json(prompt: str, temperature: float = 0) -> Dict:
    #print("[DEBUG] Entering llm_json")
    if not USE_LLM or client is None:
       # print("[DEBUG] LLM disabled, using fallback parser")
        return {"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                "symptoms": {"present": False}}

    msg = [
        {"role": "system", "content": "Return ONLY valid JSON. No prose."},
        {"role": "user", "content": prompt}
    ]
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msg,
            temperature=temperature
        )
        content = resp.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
       # print(f"[DEBUG] LLM request failed: {e}")
        return {"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                "symptoms": {"present": False}}


def parse_patient_input(user_input: str, last_patient_id: Optional[str]) -> Dict:
    # extraction includes symptoms for triage
    print(f"[DEBUG] parse_patient_input called with input: {user_input}")
    prompt = f"""
Parse the following patient message and extract structured fields. Return ONLY JSON.
Fields:
- action: one of ["reschedule", "cancel", "check_status", "schedule_new", "general"]
- patient_id: 8-digit if present else null
- preferred_date: text like "Thursday 2pm", "next week", ISO if present else null
- reason: short text explaining why they want change, else null
- symptoms: {{"present": bool, "list": [string], "severity_0_10": int|null, "fever_f": float|null, "onset_desc": string|null}}
- caregiver: {{"is_caregiver": bool, "consent_claimed": bool}}
- minor: {{"stated_age": int|null}}

Input: "{user_input}"
    """.strip()
    parsed = llm_json(prompt, temperature=0)
   # print(f"[DEBUG] parse_patient_input got back: {parsed}")
    # Simple regex fallback for patient id
    import re
    m = re.search(r'\b\d{8}\b', user_input)
    if m and not parsed.get("patient_id"):
        parsed["patient_id"] = m.group(0)
    if not parsed.get("patient_id") and last_patient_id:
        parsed["patient_id"] = last_patient_id
    return parsed

# -----------------------------
# Triage & Policy
# -----------------------------

def triage_category(symptoms: Dict) -> Tuple[str, List[str]]:
    """Return tier ('RED'|'ORANGE'|'GREEN') and matched rules."""
    if not symptoms or not symptoms.get("present"):
        return "GREEN", []
    matched = []

    text_blob = " ".join([s.lower() for s in symptoms.get("list", [])])
    sev = symptoms.get("severity_0_10")
    fever = symptoms.get("fever_f")
    # RED
    for rule in POLICY["red_flags"]:
        name, patt, thr = rule["name"], rule["pattern"], rule.get("threshold")
        if any(p in text_blob for p in patt):
            if name == "fever_high" and fever is not None:
                if fever >= thr:
                    return "RED", [name]
            elif name == "severe_pain" and sev is not None:
                if sev >= thr:
                    return "RED", [name]
            elif name not in ["fever_high", "severe_pain"]:
                return "RED", [name]
    # ORANGE
    for rule in POLICY["orange_flags"]:
        name, patt = rule["name"], rule["pattern"]
        rng = rule.get("range")
        thr = rule.get("threshold")
        if any(p in text_blob for p in patt):
            if rng and sev is not None and name == "moderate_pain":
                low, high = rng
                if low <= sev <= high:
                    return "ORANGE", [name]
            elif thr and name == "fever_low" and fever is not None:
                low, high = rng
                if low <= fever <= high:
                    return "ORANGE", [name]
            elif thr and name == "hyperglycemia":
                # look for glucose not numeric in blob; rely on LLM numeric field later if needed
                return "ORANGE", [name]
            else:
                return "ORANGE", [name]
    return "GREEN", []

def check_policy_gates(appt: pd.Series, patient_row: pd.Series, intent: str, visit_context: Dict) -> Tuple[bool, str]:
    # minors
    if patient_row["age"] < 18 and visit_context.get("caregiver_required", True):
        cg_id = patient_row["primary_caregiver_id"]
        if not cg_id:
            return False, "A caregiver must be present or consent on file for minors."
        cg = caregivers[caregivers["caregiver_id"] == cg_id]
        if cg.empty or not bool(cg.iloc[0]["consent_on_file"]):
            return False, "Caregiver consent must be on file to proceed for minors."

    # referral/authorization
    if appt.get("plan_id") in POLICY["referral_required_plans"]:
        # In a real system, check auth/ referral table
        # Here we assume it is not yet confirmed for demonstration
        if intent in ["schedule_new", "reschedule"]:
            return False, "Referral/authorization is required for this plan. I can request it and hold a slot."

    # telehealth check (if user explicitly requests video)
    requested_modality = visit_context.get("requested_modality")
    if requested_modality == "video":
        allowed = POLICY["telehealth_allowed"].get(appt["appointment_type"], True)
        if not allowed:
            return False, "This appointment type requires an in-person visit."

    # post-op window (if surgery type)
    if "Surgery" in appt["appointment_type"]:
        # extract procedure
        if "Cardiac Bypass" in appt["appointment_type"]:
            mn, mx = POLICY["postop_windows"]["Cardiac Bypass"]
        elif "Valve Repair" in appt["appointment_type"]:
            mn, mx = POLICY["postop_windows"]["Valve Repair"]
        else:
            mn, mx = (7, 14)
        # if attempting to reschedule beyond mx - block
        # We check desired_dt if provided
        desired_dt: Optional[datetime] = visit_context.get("desired_dt")
        surgery_dt = to_dt(appt["appointment_date"])  # using existing appt as anchor
        if desired_dt:
            delta_days = (desired_dt - surgery_dt).days
            if delta_days > mx:
                return False, f"First post-op evaluation must occur within {mn}-{mx} days."
    return True, ""

# -----------------------------
# Appointment Service Logic
# -----------------------------

class AppointmentService:
    def __init__(self):
        pass

    def lookup_appointment(self, patient_id: str) -> Optional[pd.Series]:
        df = appointments_data[appointments_data["patient_id"].astype(str) == str(patient_id)]
        return df.iloc[0] if not df.empty else None


    def lookup_patient(self, patient_id: str) -> Optional[pd.Series]:
        df = patients[patients["patient_id"].astype(str) == str(patient_id)]
        return df.iloc[0] if not df.empty else None



    def check_business_rules(self, appt: pd.Series) -> Dict:
        # stricter rules for surgeries within 48 hours or 'high' urgency
        appt_dt = to_dt(appt["appointment_date"])
        if "Surgery" in appt["appointment_type"] and (appt_dt - datetime.now()) < timedelta(hours=48):
            return {"can_reschedule": False, "reason": "Surgery cannot be rescheduled within 48 hours."}
        if appt["urgency"] == "high":
            return {"can_reschedule": False, "reason": "High-urgency appointments need supervisor approval."}
        return {"can_reschedule": True, "reason": ""}

    def find_alternatives(self, appt: pd.Series, constraints: Dict) -> List[str]:
        # filter slots by doctor + type; extend to location/modality/date range as needed
        slots = available_slots[
            (available_slots["doctor"] == appt["doctor"]) &
            (available_slots["appointment_type"] == appt["appointment_type"])
        ]
        # apply preferred date range if exists
        start: Optional[datetime] = constraints.get("start")
        end: Optional[datetime] = constraints.get("end")
        if start or end:
            mask = [True] * len(slots)
            for i, (_, row) in enumerate(slots.iterrows()):
                dt = to_dt(row["date"])
                if start and dt < start:
                    mask[i] = False
                if end and dt > end:
                    mask[i] = False
            slots = slots[mask]
        alts = []
        for _, row in slots.iterrows():
            dt = to_dt(row["date"]).strftime("%B %d at %I:%M %p")
            alts.append(f"{dt} ({row['location']}, {row['modality']})")
        return alts[:3]

    def process(self, parsed: Dict, use_voice: bool = False) -> str:
        try:
            pid = parsed.get("patient_id")
            intent = parsed.get("action") or "general"

            if not pid:
                msg = "Please provide your 8-digit patient ID to proceed."
                say(msg, "Agent", use_voice)
                return msg

            appt = self.lookup_appointment(pid)
            patient_row = self.lookup_patient(pid)

            if patient_row is None:
                msg = f"I could not find any patient records for ID {pid}."
                say(msg, "Agent", use_voice)
                return msg

            if appt is None:
                msg = f"I found patient {patient_row['name']}, but there are no active appointments on file. Would you like to schedule a new one?"
                say(msg, "Agent", use_voice)
                return msg

            # TRIAGE
            triage, rules = triage_category(parsed.get("symptoms", {}))
            if triage == "RED":
                msg = "Your symptoms may be serious. Please go to the nearest emergency department now. I am alerting the on-call nurse."
                say(msg, "Agent", use_voice)
                return msg
            if triage == "ORANGE":
                msg = "I will have a nurse call you today to review your symptoms. I can place a tentative hold for a visit in the next 24–48 hours."
                say(msg, "Agent", use_voice)
                return msg

            # GREEN → continue with policy gates & scheduling
            preferred_date_text = parsed.get("preferred_date")
            desired_dt = None
            visit_context = {
                "requested_modality": "video" if (preferred_date_text and "video" in preferred_date_text.lower()) else None,
                "desired_dt": desired_dt,
                "caregiver_required": True
            }
            ok, reason = check_policy_gates(appt, patient_row, intent, visit_context)
            if not ok:
                msg = f"{reason}"
                say(msg, "Agent", use_voice)
                return msg

            if intent == "check_status":
                msg = f"Your {appt_summary(appt)} is confirmed."
                say(msg, "Agent", use_voice)
                return msg
            elif intent == "cancel":
                msg = f"I can cancel your {appt_summary(appt)}. Please confirm to proceed."
                say(msg, "Agent", use_voice)
                return msg
            elif intent in ["reschedule", "schedule_new", "general"]:
                rules_check = self.check_business_rules(appt)
                if not rules_check["can_reschedule"]:
                    msg = f"Rescheduling is blocked: {rules_check['reason']}"
                    say(msg, "Agent", use_voice)
                    return msg

                constraints = {"start": datetime.now(), "end": datetime.now() + timedelta(days=14)}
                alts = self.find_alternatives(appt, constraints)
                if alts:
                    msg = f"I can offer these times: {', '.join(alts)}. Which works best?"
                else:
                    msg = "No matching slots with this provider in the next two weeks. I can check other providers or locations."
                say(msg, "Agent", use_voice)
                return msg

            # fallback
            msg = "I can help with checking status, scheduling, rescheduling, or canceling. What would you like to do?"
            say(msg, "Agent", use_voice)
            return msg

        except Exception as e:
            msg = f"⚠️ Error while processing: {str(e)}"
            say(msg, "Agent", use_voice)
            return msg


# -----------------------------
# Q&A Generation (LLM) + Evaluator
# -----------------------------

QNA_SEED = [
    "I had heart surgery last week; pain is 8/10 with shortness of breath. I want to move my follow-up.",
    "I am patient {pid}; can I push my first follow-up to day 21 after surgery?",
    "I am patient {pid}; low-grade fever 100.8 on day 5. Next week OK?",
    "I need suture removal—can this be video?",
    "I am 17; can I reschedule to next Thursday afternoon?",
    "My glucose was over 320; I feel a bit dizzy. I want a visit this week.",
    "I only need medication review—video preferred.",
    "I need forms signed; can we do tomorrow morning?",
    "Transportation is hard; Fridays only.",
    "My incision has yellow drainage and is opening.",
    "I want to move my surgery to next week.",
]

def generate_qna_examples(n: int = 20) -> List[Dict]:
    examples: List[Dict] = []
    # Use IDs from patients table
    ids = list(patients["patient_id"])
    import random
    for i in range(n):
        seed = random.choice(QNA_SEED)
        seed = seed.replace("{pid}", random.choice(ids))
        if USE_LLM and client is not None:
            prompt = f"""
You are creating one realistic patient scheduling utterance for a post-cardiac-surgery clinic.
Return ONLY JSON:
{{
  "user_text": "... one sentence ...",
  "rationale": "brief why this is realistic",
  "expected_tier": "RED|ORANGE|GREEN"
}}
Guidance: consider symptoms, minors, telehealth, referral, policy windows, caregiver availability.
Seed idea: "{seed}"
            """
            j = llm_json(prompt, temperature=0.7)
            if "user_text" in j:
                examples.append(j)
            else:
                examples.append({"user_text": seed, "rationale": "seed fallback", "expected_tier": "GREEN"})
        else:
            # No LLM fallback: simple seed
            examples.append({"user_text": seed, "rationale": "seed only", "expected_tier": "GREEN"})
    return examples

def evaluate_examples(examples: List[Dict]) -> pd.DataFrame:
    rows = []
    service = AppointmentService()
    last_pid = None
    for ex in examples:
        parsed = parse_patient_input(ex["user_text"], last_pid)
        last_pid = parsed.get("patient_id") or last_pid
        triage, _ = triage_category(parsed.get("symptoms", {}))
        expected = ex.get("expected_tier")
        rows.append({
            "user_text": ex["user_text"],
            "parsed_pid": parsed.get("patient_id"),
            "triage": triage,
            "expected_tier": expected,
            "match": (expected == triage) if expected in ["RED","ORANGE","GREEN"] else None
        })
    return pd.DataFrame(rows)

# -----------------------------
# Demo Runner
# -----------------------------

class AppointmentDemo:
    def __init__(self, use_voice: bool = False):
        self.use_voice = use_voice
        self.service = AppointmentService()
        self.last_patient_id: Optional[str] = None

    def run_turn(self, text: str) -> Dict:
        say(text, "Patient", self.use_voice)
        parsed = parse_patient_input(text, self.last_patient_id) or {}
        if parsed.get("patient_id"):
            self.last_patient_id = parsed["patient_id"]

        #print(f"[DEBUG] Parsed: {parsed}")  # show what was extracted
        response = self.service.process(parsed, use_voice=self.use_voice)
        #print(f"[DEBUG] Agent responded with: {response}")  # guarantee visible
        return {"request": parsed, "response": response}


if __name__ == "__main__":
    print("Multi-Agent Appointment System (LLM + Rules)")
    print("Type 'gen' to auto-generate 20 Q&A examples and evaluate.")
    print("Type 'quit' to exit.")

    demo = AppointmentDemo(use_voice=False)
    while True:
        user = input("\nPatient: ")
        if user.strip().lower() == "quit":
            break

        elif user.strip().lower() == "gen":
            ex = generate_qna_examples(20)

            # Force more IDs into examples
            ids = list(patients["patient_id"])
            import random
            for e in ex:
                if not any(pid in e["user_text"] for pid in ids):
                    # inject a random patient ID 70% of the time
                    if random.random() < 0.7:
                        e["user_text"] = f"I am patient {random.choice(ids)}, {e['user_text']}"

            print("\nGenerated Q&A Examples:")

            demo = AppointmentDemo(use_voice=False)
            results = []
            for i, e in enumerate(ex, 1):  # loop through all 20
                patient_text = e["user_text"]
                turn = demo.run_turn(patient_text)

                # If no ID → still allow triage responses
                parsed = turn["request"]
                pid = parsed.get("patient_id")
                triage, _ = triage_category(parsed.get("symptoms", {}))
                agent_answer = turn["response"]
                if not pid:
                    if triage == "RED":
                        agent_answer = "Your symptoms may be serious. Please go to the nearest emergency department now. I am alerting the on-call nurse."
                    elif triage == "ORANGE":
                        agent_answer = "I will have a nurse call you today to review your symptoms. I can place a tentative hold for a visit in the next 24–48 hours."

                # Print first 5 only (so terminal isn’t too long)
                if i <= 5:
                    print(f"\n{i}.")
                    print(f"Patient: {patient_text}")
                    print(f"Agent:   {agent_answer}")
                    print(f"Triage:  {triage} (expected: {e.get('expected') or e.get('expected_tier')})")

                results.append({
                    "patient": patient_text,
                    "agent": agent_answer,
                    "triage": triage,
                    "expected": e.get("expected") or e.get("expected_tier")
                })

            # Save to JSON
            with open(os.path.join(QNA_DIR, "generated_qna_examples.json"), "w") as f:
                json.dump(results, f, indent=2)

            # Save to CSV
            df = pd.DataFrame(results)
            df.to_csv(os.path.join(QNA_DIR, "generated_qna_examples.csv"), index=False)

            print(f"\n✅ Saved 20 Q&A examples to:")
            print(f"   {os.path.join(QNA_DIR, 'generated_qna_examples.json')}")
            print(f"   {os.path.join(QNA_DIR, 'generated_qna_examples.csv')}")

        else:
            # 👇 handle normal patient messages
            turn = demo.run_turn(user)
            print(f"Agent: {turn['response']}")
