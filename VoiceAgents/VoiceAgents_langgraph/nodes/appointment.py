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
    from ..utils.logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    restrictions_str = ", ".join(AGENT_POLICY.get("restrictions", []))
    logger.info(f"[Policy] Appointment Agent loaded: scope=[{scope_str}], restrictions=[{restrictions_str}]")

# Load data from CSV files
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
appointments_data = pd.read_csv(os.path.join(DATA_DIR, "appointments.csv"))
available_slots = pd.read_csv(os.path.join(DATA_DIR, "available_slots.csv"))
patients = pd.read_csv(os.path.join(DATA_DIR, "patients.csv"))
caregivers = pd.read_csv(os.path.join(DATA_DIR, "caregivers.csv"))

# Handle chronic_conditions: convert from string to list if needed
if "chronic_conditions" in patients.columns:
    def parse_conditions(val):
        if pd.isna(val) or val == "None" or val == "":
            return []
        if isinstance(val, list):
            return val
        # Split comma-separated string
        return [c.strip() for c in str(val).split(",") if c.strip()]
    patients["chronic_conditions"] = patients["chronic_conditions"].apply(parse_conditions)

# Handle consent_on_file: convert to boolean
if "consent_on_file" in caregivers.columns:
    caregivers["consent_on_file"] = caregivers["consent_on_file"].astype(bool)

# Load triage policy from JSON file
TRIAGE_POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "appointment_triage_policy.json")
POLICY = {}
if os.path.exists(TRIAGE_POLICY_PATH):
    with open(TRIAGE_POLICY_PATH, "r") as f:
        POLICY = json.load(f)
    # Convert JSON arrays back to tuples for postop_windows (for compatibility with existing code)
    if "postop_windows" in POLICY:
        for key, value in POLICY["postop_windows"].items():
            if isinstance(value, list):
                POLICY["postop_windows"][key] = tuple(value)
    # Convert JSON arrays back to tuples for orange_flags ranges
    if "orange_flags" in POLICY:
        for flag in POLICY["orange_flags"]:
            if "range" in flag and isinstance(flag["range"], list):
                flag["range"] = tuple(flag["range"])
else:
    # Fallback to empty policy if file doesn't exist
    POLICY = {
        "postop_windows": {},
        "telehealth_allowed": {},
        "referral_required_plans": [],
        "red_flags": [],
        "orange_flags": []
    }


def to_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def appt_summary(appt: pd.Series) -> str:
    dt = to_dt(appt["appointment_date"]).strftime("%B %d at %I:%M %p")
    return f"{appt['appointment_type']} with {appt['doctor']} on {dt}"


def llm_json(prompt: str, temperature: float = 0) -> Tuple[Dict, Optional[str], Optional[str], Optional[int]]:
    """Returns (parsed_dict, provider, model, latency_ms) tuple"""
    if not USE_LLM:
        return ({"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                "symptoms": {"present": False}}, None, None, None)
    msg = [
        {"role": "system", "content": "Return ONLY valid JSON. No prose."},
        {"role": "user", "content": prompt}
    ]
    try:
        result = chat_completion(messages=msg, temperature=temperature, model=get_default_model())
        if not result:
            return ({"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                    "symptoms": {"present": False}}, None, None, None)
        # Handle tuple return: (text, provider, model, latency_ms) or (text, provider, model)
        if isinstance(result, tuple):
            if len(result) == 4:
                content, provider, model, latency_ms = result
            else:
                content, provider, model = result[:3]
                latency_ms = result[3] if len(result) > 3 else None
        else:
            content = result
            provider = None
            model = None
            latency_ms = None
        if not content:
            return ({"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                    "symptoms": {"present": False}}, provider, model, latency_ms)
        return (json.loads(content.strip()), provider, model, latency_ms)
    except Exception:
        return ({"action": "general", "patient_id": None, "preferred_date": None, "reason": None,
                "symptoms": {"present": False}}, None, None, None)


def parse_patient_input(user_input: str, last_patient_id: Optional[str]) -> Tuple[Dict, Optional[str], Optional[str], Optional[int]]:
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
    parsed, provider, model, latency_ms = llm_json(prompt, temperature=0)
    
    # Simple regex fallback for patient id
    m = re.search(r'\b\d{8}\b', user_input)
    if m and not parsed.get("patient_id"):
        parsed["patient_id"] = m.group(0)
    if not parsed.get("patient_id") and last_patient_id:
        parsed["patient_id"] = last_patient_id
    return (parsed, provider, model, latency_ms)


def triage_category(symptoms: Dict) -> Tuple[str, List[str]]:
    """Return tier ('RED'|'ORANGE'|'GREEN') and matched rules.

    PHASE 2 ENHANCEMENT (Based on Heather's Clinical Feedback):
    Before auto-escalating RED flags to ER, add probing questions to gather context:

    For HIGH FEVER (≥101.5°F):
        - Ask: "Do you have flu-like symptoms (body aches, cough, runny nose)?"
        - Ask: "When did the fever start?"
        - Ask: "Have you taken fever-reducing medication?"
        → If flu symptoms present: Route to nurse callback (not ER)
        → If post-op or sudden onset with no flu: Route to ER

    For SEVERE PAIN (≥8/10):
        - Ask: "What type of pain? (sharp, dull, burning, throbbing)"
        - Ask: "Where exactly is the pain?"
        - Ask: "Is this new pain or has it been ongoing?"
        → New sharp chest pain: ER
        → Chronic pain flare-up: Nurse callback + pain management
        → Post-op pain at surgical site: Surgeon office visit

    For WOUND ISSUES (pus, drainage, opening):
        - Ask: "How much drainage? (small amount, large amount, continuous)"
        - Ask: "What color? (clear, yellow, green, bloody)"
        - Ask: "How much has incision opened? (small gap, large opening)"
        → Minor pus + small opening: Surgeon office visit
        → Heavy green drainage + large opening: ER
        → Mild redness only: Nurse callback

    For DIZZINESS:
        - Ask: "Experiencing chest pain, shortness of breath, weakness, slurred speech with it?"
        - Ask: "Did it come on suddenly or gradually?"
        → With stroke/cardiac symptoms: ER
        → Isolated dizziness: Warm transfer to RN
    """
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
            elif rng and name == "fever_low" and fever is not None:
                # Check fever range: 99.5-101.4°F is ORANGE
                low, high = rng
                if low <= fever <= high:
                    return "ORANGE", [name]
                # If fever mentioned but outside range, skip (don't assume)
                continue
            elif name == "dizziness" or name in ["wound_redness", "hyperglycemia"]:
                # These flags don't require threshold/range checks
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
                # Check if this is a high fever case that needs probing
                is_fever_high = "fever_high" in rules
                if is_fever_high:
                    # Start fever probing phase instead of immediate ER
                    # Return a special marker that will be handled in appointment_node
                    return "__FEVER_PROBE_START__"
                else:
                    # All other RED cases: immediate ER (unchanged behavior)
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
    
    # Handle fever probing phase (multi-turn conversation)
    triage_phase = state.get("triage_phase")
    if triage_phase == "fever_probe":
        # User is answering fever probing questions
        triage_context = state.get("triage_context", {})
        user_lower = user_input.lower()
        
        # Simple decision logic based on user's answer
        # Check for flu-like symptoms (handles both singular and plural forms)
        has_flu_symptoms = any(keyword in user_lower for keyword in [
            "flu", "body ache", "body aches", "cough", "runny nose", 
            "congestion", "sore throat", "aches"
        ])
        
        # Get original fever temperature from context
        fever_temp = triage_context.get("fever_temperature")
        fever_str = f"{fever_temp:.1f}°F" if fever_temp else "high fever"
        
        # Determine escalation path
        if has_flu_symptoms:
            # Flu symptoms + high fever → Nurse callback (not ER)
            escalation_path = "warm_transfer_rn"
            response = f"Thank you for answering those questions. Based on your responses, you have flu-like symptoms along with your {fever_str} fever. This combination is often expected with the flu and typically doesn't require emergency care. I'm connecting you with a nurse right now who can provide guidance and help determine if you need to be seen sooner."
        else:
            # High fever without flu symptoms → ER (more serious)
            escalation_path = "er"
            response = f"Thank you for answering those questions. Based on your responses, your {fever_str} fever without flu-like symptoms could indicate something more serious. Please go to the nearest emergency department right away. I'm also alerting the on-call nurse about this."
        
        # Update state and clear probing phase
        state["triage_phase"] = None
        state["triage_context"] = None
        state["escalation_path"] = escalation_path
        state["appointment_response"] = response
        state["response"] = response
        
        # Log the decision
        log_entry = {
            "ts": now_iso(),
            "agent": "AppointmentAgent",
            "patient_id": patient_id,
            "input": user_input,
            "response": response,
            "triage_phase": "fever_probe_completed",
            "escalation_path": escalation_path,
            "triage_context": triage_context
        }
        state["log_entry"] = log_entry
        log_appointment(log_entry)
        
        if state.get("voice_enabled", False):
            say(response, voice=True)
        
        return state
    
    service = AppointmentService()
    parsed_result = parse_patient_input(user_input, patient_id)
    # parse_patient_input now returns (parsed_dict, provider, model, latency_ms)
    if isinstance(parsed_result, tuple):
        if len(parsed_result) == 4:
            parsed, llm_provider, llm_model, latency_ms = parsed_result
        else:
            parsed, llm_provider, llm_model = parsed_result[:3]
            latency_ms = parsed_result[3] if len(parsed_result) > 3 else None
    else:
        parsed = parsed_result
        llm_provider = None
        llm_model = None
        latency_ms = None
    
    response = service.process(parsed, use_voice=state.get("voice_enabled", False))
    
    # Check if service returned fever probe start marker
    if response == "__FEVER_PROBE_START__":
        # Initialize fever probing phase
        symptoms = parsed.get("symptoms", {})
        fever_temp = symptoms.get("fever_f")
        
        # Set up probing phase
        state["triage_phase"] = "fever_probe"
        state["triage_context"] = {
            "initial_symptoms": symptoms,
            "fever_temperature": fever_temp,
            "user_input": user_input,
            "originating_agent": "appointment"  # Track which agent started the probe
        }
        
        # DEBUG: Log that we're setting up probing phase
        logger.info(f"[DEBUG] AppointmentAgent - Setting triage_phase to 'fever_probe' (patient: {patient_id}, session: {state.get('session_id')})")
        
        # Ask probing questions
        response = "I understand you're experiencing a high fever. To help determine the best course of action, I need to ask a few quick questions: "
        response += "Do you have any flu-like symptoms, such as body aches, cough, or runny nose? "
        response += "When did the fever start? "
        response += "And have you taken any fever-reducing medication like Tylenol or Advil?"
        
        state["appointment_response"] = response
        state["response"] = response
        
        # Log the start of probing phase
        log_entry = {
            "ts": now_iso(),
            "agent": "AppointmentAgent",
            "patient_id": patient_id,
            "input": user_input,
            "parsed": parsed,
            "response": response,
            "provider": llm_provider,
            "model": llm_model,
            "latency_ms": latency_ms,
            "triage_phase": "fever_probe_started",
            "actions": {"action": parsed.get("action")},
            "policies": {"policies_applied": ["triage_required"]}
        }
        state["log_entry"] = log_entry
        log_appointment(log_entry)
        
        if state.get("voice_enabled", False):
            say(response, voice=True)
        
        return state
    
    state["appointment_response"] = response
    state["response"] = response
    state["parsed_data"] = parsed
    
    # Extract actions from actual parsed data (not hardcoded mapping)
    # Use the actual action from parsing, don't transform it
    actions = {
        "action": parsed.get("action"),           # Actual action from LLM/parsing
        "preferred_date": parsed.get("preferred_date"),  # Actual date if provided
        "reason": parsed.get("reason")             # Actual reason if provided
    }
    
    # Extract policies that were actually applied/checked during processing
    # Check what policies were relevant based on the actual processing
    policies_applied = []
    symptoms = parsed.get("symptoms", {})
    if symptoms.get("present"):  # Triage was performed if symptoms present
        policies_applied.append("triage_required")
    if parsed.get("minor", {}).get("stated_age"):  # Minor consent check was performed
        policies_applied.append("minor_consent_check")
    
    policies = {
        "policies_applied": policies_applied,  # Only policies that were actually checked
        "scope": AGENT_POLICY.get("scope", []),  # Available scope from policy file
        "triage_required": AGENT_POLICY.get("triage_required", False)  # From policy file
    }
    
    # Log entry with provider/model info
    log_entry = {
        "ts": now_iso(),
        "agent": "AppointmentAgent",
        "patient_id": patient_id,
        "input": user_input,
        "parsed": parsed,
        "response": response,
        "provider": llm_provider,
        "model": llm_model,
        "latency_ms": latency_ms,  # Store latency for conversation log
        "actions": actions,
        "policies": policies
    }
    state["log_entry"] = log_entry
    log_appointment(log_entry)
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

