"""
Appointment Agent Node - LangGraph implementation
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
import pandas as pd
import os
import sys
from ..state import VoiceAgentState
from ..utils import now_iso, say
from ..utils.llm_provider import chat_completion, USE_LLM, get_default_model
from ..utils.logging_utils import log_appointment

# Use local database
from ..database import DatabaseService

# Load agent-specific policy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "appointment_policy.json")
AGENT_POLICY = {}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r") as f:
        AGENT_POLICY = json.load(f)
    # Log policy summary on startup
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    restrictions_str = ", ".join(AGENT_POLICY.get("restrictions", []))
    print(f"[Policy] Appointment Agent loaded: scope=[{scope_str}], restrictions=[{restrictions_str}]")

# Mock data (same as original)
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

POLICY = {
    "postop_windows": {
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
        {"name": "chest_pain", "pattern": ["chest pain", "pain in my chest", "chest tightness", "tightness in my chest"], "threshold": None},
        {"name": "shortness_of_breath", "pattern": ["shortness of breath", "short of breath", "trouble breathing"], "threshold": None},
        {"name": "wound_dehiscence", "pattern": ["incision opening", "wound opening", "dehiscence", "yellow drainage", "pus", "green drainage", "greenish fluid", "ooze", "warm to the touch", "warm", "swelling"], "threshold": None},
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
        {"name": "wound_redness", "pattern": ["redness"], "threshold": None},
        {"name": "dizziness", "pattern": ["dizzy", "dizziness"], "threshold": None},
    ]
}


def to_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def appt_summary(appt: pd.Series) -> str:
    dt = to_dt(appt["appointment_date"]).strftime("%B %d at %I:%M %p")
    return f"{appt['appointment_type']} with {appt['doctor']} on {dt}"


def llm_json(prompt: str, temperature: float = 0) -> Dict:
    if not USE_LLM:
        return {"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                "symptoms": {"present": False}}
    msg = [
        {"role": "system", "content": "Return ONLY valid JSON. No prose."},
        {"role": "user", "content": prompt}
    ]
    try:
        content = chat_completion(messages=msg, temperature=temperature, model=get_default_model())
        if not content:
            return {"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                    "symptoms": {"present": False}}
        return json.loads(content.strip())
    except Exception:
        return {"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                "symptoms": {"present": False}}


def parse_patient_input(user_input: str, last_patient_id: Optional[str]) -> Dict:
    # extraction includes symptoms for triage
    # Note: Debug print removed for cleaner output - can be re-enabled if needed
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
    
    # Simple regex fallback for patient id
    m = re.search(r'\b\d{8}\b', user_input)
    if m and not parsed.get("patient_id"):
        parsed["patient_id"] = m.group(0)
    if not parsed.get("patient_id") and last_patient_id:
        parsed["patient_id"] = last_patient_id
    return parsed


def triage_category(symptoms: Dict) -> Tuple[str, List[str]]:
    """Return tier ('RED'|'ORANGE'|'GREEN') and matched rules."""
    if not symptoms or not symptoms.get("present"):
        return "GREEN", []
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
                return "ORANGE", [name]
            else:
                return "ORANGE", [name]
    return "GREEN", []


def check_policy_gates(appt: pd.Series, patient_row: pd.Series, intent: str, visit_context: Dict) -> Tuple[bool, str]:
    if patient_row["age"] < 18 and visit_context.get("caregiver_required", True):
        cg_id = patient_row["primary_caregiver_id"]
        if not cg_id:
            return False, "A caregiver must be present or consent on file for minors."
        cg = caregivers[caregivers["caregiver_id"] == cg_id]
        if cg.empty or not bool(cg.iloc[0]["consent_on_file"]):
            return False, "Caregiver consent must be on file to proceed for minors."
    
    if appt.get("plan_id") in POLICY["referral_required_plans"]:
        if intent in ["schedule_new", "reschedule"]:
            return False, "This request requires provider approval. I can submit that request for you, and the provider's office will contact you to confirm."
    
    requested_modality = visit_context.get("requested_modality")
    if requested_modality == "video":
        allowed = POLICY["telehealth_allowed"].get(appt["appointment_type"], True)
        if not allowed:
            return False, "This appointment type requires an in-person visit."
    
    if "Surgery" in appt["appointment_type"]:
        if "Cardiac Bypass" in appt["appointment_type"]:
            mn, mx = POLICY["postop_windows"]["Cardiac Bypass"]
        elif "Valve Repair" in appt["appointment_type"]:
            mn, mx = POLICY["postop_windows"]["Valve Repair"]
        else:
            mn, mx = (7, 14)
        desired_dt: Optional[datetime] = visit_context.get("desired_dt")
        surgery_dt = to_dt(appt["appointment_date"])
        if desired_dt:
            delta_days = (desired_dt - surgery_dt).days
            if delta_days > mx:
                return False, f"First post-op evaluation must occur within {mn}-{mx} days."
    return True, ""


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
        appt_dt = to_dt(appt["appointment_date"])
        if "Surgery" in appt["appointment_type"] and (appt_dt - datetime.now()) < timedelta(hours=48):
            return {"can_reschedule": False, "reason": "Surgery cannot be rescheduled within 48 hours."}
        if appt["urgency"] == "high":
            return {"can_reschedule": False, "reason": "High-urgency appointments need supervisor approval."}
        return {"can_reschedule": True, "reason": ""}
    
    def find_alternatives(self, appt: pd.Series, constraints: Dict) -> List[str]:
        slots = available_slots[
            (available_slots["doctor"] == appt["doctor"]) &
            (available_slots["appointment_type"] == appt["appointment_type"])
        ]
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
                return "I'd be happy to help you with your appointment. Could you please provide your 8-digit patient ID so I can look up your information?"
            
            appt = self.lookup_appointment(pid)
            patient_row = self.lookup_patient(pid)
            
            if patient_row is None:
                return f"I'm sorry, but I couldn't find any patient records with the ID {pid}. Could you please double-check your patient ID and try again?"
            
            if appt is None:
                return f"Hi {patient_row['name']}, I don't see any active appointments scheduled for you at the moment. Would you like me to help you schedule a new appointment?"
            
            # TRIAGE - check symptoms mentioned in context of appointment request
            triage, rules = triage_category(parsed.get("symptoms", {}))
            if triage == "RED":
                return "I understand you need to schedule an appointment, but based on the symptoms you've described, this sounds like it could be serious. Please go to the nearest emergency department right away. I'm also alerting the on-call nurse about this."
            if triage == "ORANGE":
                return "I hear you'd like to schedule an appointment, and I've also noted the symptoms you mentioned. Let me have a nurse call you today to discuss both your symptoms and find the best appointment time. I can also place a tentative hold for a visit in the next 24 to 48 hours."
            
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
                return reason
            
            if intent == "check_status":
                return f"Great! I can confirm that your {appt_summary(appt)} is scheduled and confirmed."
            elif intent == "cancel":
                return f"I can help you cancel your {appt_summary(appt)}. Are you sure you'd like to proceed with the cancellation?"
            elif intent in ["reschedule", "schedule_new", "general"]:
                rules_check = self.check_business_rules(appt)
                if not rules_check["can_reschedule"]:
                    return f"I understand you'd like to reschedule, but I'm unable to do that right now because: {rules_check['reason']}"
                
                constraints = {"start": datetime.now(), "end": datetime.now() + timedelta(days=14)}
                alts = self.find_alternatives(appt, constraints)
                if alts:
                    return f"I'd be happy to help you reschedule! Here are some available times that might work for you: {', '.join(alts)}. Which of these would work best for your schedule?"
                else:
                    return "I've checked for available slots with this provider in the next two weeks, and unfortunately there aren't any matching your current appointment type. Would you like me to check with other providers or at different locations?"
            
            return "I can help you with checking your appointment status, scheduling a new appointment, rescheduling, or canceling an existing one. What would you like to do today?"
        except Exception as e:
            return f"[WARNING] Error while processing: {str(e)}"


def appointment_node(state: VoiceAgentState) -> VoiceAgentState:
    """Appointment agent node"""
    user_input = state.get("user_input", "")
    patient_id = state.get("patient_id")
    
    service = AppointmentService()
    parsed = parse_patient_input(user_input, patient_id)
    response = service.process(parsed, use_voice=state.get("voice_enabled", False))
    
    state["appointment_response"] = response
    state["response"] = response
    state["parsed_data"] = parsed
    
    # Log entry
    log_entry = {
        "ts": now_iso(),
        "agent": "AppointmentAgent",
        "patient_id": patient_id,
        "input": user_input,
        "parsed": parsed,
        "response": response
    }
    state["log_entry"] = log_entry
    log_appointment(log_entry)
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

