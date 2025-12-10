"""
Medication Agent Node - LangGraph implementation
"""
import json
import os
from typing import Dict, Optional, Tuple
import pandas as pd
from ..state import VoiceAgentState
from ..utils import now_iso, say
from ..utils.llm_provider import chat_completion, USE_LLM, get_default_model
from ..utils.logging_utils import log_medication

# Use local database
from ..database import DatabaseService

# Load agent-specific policy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "medication_policy.json")
AGENT_POLICY = {}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r") as f:
        AGENT_POLICY = json.load(f)
    # Log policy summary on startup
    from ..utils.logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    logger.info(f"[Policy] Medication Agent loaded: scope=[{scope_str}], triage={AGENT_POLICY.get('triage_required', False)}")

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
KNOWLEDGE_PATH = os.path.join(DATA_DIR, "drug_knowledge.csv")
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def llm_parse_query(user_text: str) -> Tuple[Dict, Optional[str], Optional[str], Optional[int]]:
    """Use LLM to extract intent, drugs, and symptoms.
    Returns: (parsed_dict, provider, model) tuple"""
    if not USE_LLM:
        text = user_text.lower()
        intent = "general"
        if "miss" in text or "forgot" in text:
            intent = "missed_dose"
        elif "double" in text or "two doses" in text:
            intent = "double_dose"
        elif "side effect" in text or "feel" in text or "dizzy" in text:
            intent = "side_effect"
        elif "interact" in text or "together" in text or "combine" in text:
            intent = "interaction_check"
        elif "how" in text or "take" in text or "food" in text or "meal" in text:
            intent = "instruction"
        elif "pregnan" in text or "kidney" in text or "liver" in text:
            intent = "contraindication"
        elif "prescription" in text or "dosage" in text or "dose" in text or "taking" in text or "medication" in text:
            intent = "prescription_info"
        return ({"intent": intent, "language": "en"}, None, None, None)
    
    sys_msg = {"role": "system", "content": "Return ONLY valid JSON. No prose."}
    user = {
        "role": "user",
        "content": f"""
Parse this medication question. Return JSON with:
- intent: one of ["missed_dose","double_dose","side_effect","interaction_check","instruction","contraindication","prescription_info","general"]
- drugs_mentioned: [{{"raw":string,"norm_name":string|null}}]
- language: "en"

Question: "{user_text}"
""",
    }
    try:
        messages = [sys_msg, user]
        result = chat_completion(messages=messages, temperature=0, model=get_default_model())
        if not result:
            return ({"intent": "general", "language": "en"}, None, None, None)
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
            return ({"intent": "general", "language": "en"}, provider, model, latency_ms)
        return (json.loads(content.strip()), provider, model, latency_ms)
    except Exception:
        return ({"intent": "general", "language": "en"}, None, None, None)


def llm_score_risk(parsed: Dict) -> Tuple[str, Optional[str], Optional[str], Optional[int]]:
    """Return (risk_level, provider, model) tuple.
    Risk level is RED / ORANGE / GREEN.

    HEATHER FEEDBACK (Rows 10, 12): Double dose shouldn't be HIGH RISK unless patient has symptoms.
    """
    if not USE_LLM:
        intent = parsed.get("intent")
        if intent == "double_dose":
            # Check if patient is experiencing symptoms (Heather feedback Rows 10, 12)
            symptoms = parsed.get("symptoms", {})
            has_symptoms = symptoms.get("present", False) if isinstance(symptoms, dict) else False
            # Only RED if they have symptoms; otherwise ORANGE for monitoring
            return ("RED" if has_symptoms else "ORANGE", None, None, None)
        if intent in ["interaction_check", "missed_dose"]:
            return ("ORANGE", None, None, None)
        # Contraindication general questions should be GREEN (Heather feedback Row 45)
        if intent == "contraindication":
            return ("GREEN", None, None, None)
        return ("GREEN", None, None, None)
    
    messages = [
        {"role": "system", "content": "Return ONLY a single word: RED, ORANGE, or GREEN. Important: Double dose should be ORANGE unless patient has symptoms (then RED). Contraindication general questions should be GREEN."},
        {"role": "user", "content": json.dumps(parsed, ensure_ascii=False)}
    ]
    try:
        result = chat_completion(messages=messages, temperature=0, model=get_default_model())
        if not result:
            return ("GREEN", None, None, None)
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
            return ("GREEN", provider, model, latency_ms)
        return (content.strip().upper(), provider, model, latency_ms)
    except Exception:
        return ("GREEN", None, None, None)


class MedicationService:
    def __init__(self):
        self.db = DatabaseService()
        self.drug_knowledge = self._load_drug_knowledge()
    
    def _load_drug_knowledge(self) -> pd.DataFrame:
        if not os.path.exists(KNOWLEDGE_PATH):
            return pd.DataFrame()
        return pd.read_csv(KNOWLEDGE_PATH)
    
    def _get_drug_info(self, name: str) -> Optional[dict]:
        df = self.drug_knowledge
        match = df[df["drug_name"].str.lower() == name.lower()]
        return match.iloc[0].to_dict() if not match.empty else None
    
    def handle(self, patient_id: str, user_text: str, use_voice: bool = False) -> Tuple[str, Dict, str, Optional[str], Optional[str], Optional[int]]:
        """Handle medication query and return (response, parsed, risk, provider, model, latency_ms)"""
        patient = self.db.get_patient(patient_id)
        if not patient:
            return ("Patient not found.", {}, "GREEN", None, None, None)
        
        parsed, parse_provider, parse_model, parse_latency = llm_parse_query(user_text)
        intent = parsed.get("intent", "general")
        
        prescriptions = self.db.get_prescriptions(patient_id)
        if not prescriptions:
            return ("No prescriptions found for this patient.", parsed, "GREEN", parse_provider, parse_model, parse_latency)

        risk, risk_provider, risk_model, risk_latency = llm_score_risk(parsed)

        # Use provider/model from the last LLM call (risk scoring), or fallback to parse call
        llm_provider = risk_provider or parse_provider
        llm_model = risk_model or parse_model
        # Sum latencies from both LLM calls
        total_latency = (parse_latency or 0) + (risk_latency or 0) if (parse_latency or risk_latency) else None

        # CRITICAL FIX: Only discuss medications that user asked about
        # Extract drug names mentioned in user's question
        drugs_mentioned = parsed.get("drugs_mentioned", [])
        mentioned_drug_names = []
        if drugs_mentioned:
            for drug in drugs_mentioned:
                if isinstance(drug, dict):
                    # Try normalized name first, then raw
                    drug_name = drug.get("norm_name") or drug.get("raw")
                    if drug_name:
                        mentioned_drug_names.append(drug_name.lower())
                elif isinstance(drug, str):
                    mentioned_drug_names.append(drug.lower())

        # Filter prescriptions to only those mentioned (or all if it's a general query)
        filtered_prescriptions = prescriptions
        if mentioned_drug_names and intent not in ["general", "prescription_info"]:
            # User asked about specific drug(s) - only show those
            filtered_prescriptions = [
                p for p in prescriptions
                if any(mentioned_name in p["drug_name"].lower() for mentioned_name in mentioned_drug_names)
            ]
            # If no matches found, fallback to all prescriptions with a note
            if not filtered_prescriptions:
                filtered_prescriptions = prescriptions

        # CRITICAL FIX: Hypoglycemia requires immediate urgency (Heather feedback Row 55)
        # Check for low blood sugar symptoms - this is time-sensitive
        user_lower = user_text.lower()
        hypoglycemia_keywords = ["low blood sugar", "blood sugar is low", "hypoglycemia", "hypoglycemic",
                                  "shaky after insulin", "dizzy after insulin", "sweating after insulin"]
        if any(keyword in user_lower for keyword in hypoglycemia_keywords):
            # Override risk to RED - this is urgent
            risk = "RED"
            urgent_response = "[URGENT - HYPOGLYCEMIA] Low blood sugar can be serious. "
            urgent_response += "If you can, check your blood sugar level now. "
            urgent_response += "Eat or drink 15g of fast-acting carbs (juice, glucose tablets, or candy). "
            urgent_response += "I'm connecting you to a nurse RIGHT NOW for immediate guidance. "
            urgent_response += "If you feel confused, have seizures, or can't swallow, call 911 immediately."
            return (urgent_response, parsed, risk, llm_provider, llm_model, total_latency)

        responses = []
        for p in filtered_prescriptions:
            # Handle prescription_info intent - show actual prescription data from database
            if intent == "prescription_info":
                # Use actual prescription data from database (safe to share per policy)
                dose = p.get("dose", "N/A")
                frequency = p.get("frequency", "N/A")
                route = p.get("route", "oral")
                condition = p.get("condition", "")
                responses.append(f"{p['drug_name']}: {dose} {frequency} ({route}) for {condition}.")
                continue
            
            # For other intents, use drug knowledge base
            info = self._get_drug_info(p["drug_name"])
            if not info:
                # If no drug knowledge, at least show prescription info
                dose = p.get("dose", "N/A")
                frequency = p.get("frequency", "N/A")
                responses.append(f"{p['drug_name']}: {dose} {frequency}.")
                continue
            
            if intent == "side_effect":
                responses.append(f"{p['drug_name']}: Common side effects include {info['common_side_effects']}.")
            elif intent == "missed_dose":
                responses.append(f"{p['drug_name']}: {info['missed_dose_advice']}.")
            elif intent == "interaction_check":
                responses.append(f"{p['drug_name']}: {info['serious_interactions']}.")
            elif intent == "instruction":
                responses.append(f"{p['drug_name']}: {info['food_advice']}.")
            elif intent == "contraindication":
                responses.append(f"{p['drug_name']}: Contraindicated in {info['contraindications']}.")
            else:
                # For general queries, show both prescription info and drug class
                dose = p.get("dose", "")
                frequency = p.get("frequency", "")
                if dose and frequency:
                    responses.append(f"{p['drug_name']}: {dose} {frequency} for {p.get('condition', '')} ({info.get('drug_class', 'Unknown')} class).")
                else:
                    responses.append(f"{p['drug_name']} is used for {p.get('condition', '')} ({info.get('drug_class', 'Unknown')} class).")
        
        if intent == "interaction_check" and len(responses) > 1:
            responses.insert(0, "You're taking multiple medications. Here are the interaction warnings:")
        
        if not responses:
            responses.append("I could not interpret your medication question clearly.")
        
        combined = " ".join(responses)
        if risk == "RED":
            combined = "[HIGH RISK] Please seek immediate medical care. " + combined
        elif risk == "ORANGE":
            combined = "[ALERT] Please contact your clinician soon. " + combined
        
        return (combined, parsed, risk, llm_provider, llm_model, total_latency)


def medication_node(state: VoiceAgentState) -> VoiceAgentState:
    """Medication agent node"""
    user_input = state.get("user_input", "")
    patient_id = state.get("patient_id")
    
    if not patient_id:
        response = "Please provide your 8-digit patient ID for medication information."
        state["medication_response"] = response
        state["response"] = response
        return state
    
    service = MedicationService()
    response, parsed, risk, llm_provider, llm_model, latency_ms = service.handle(
        patient_id, user_input, use_voice=state.get("voice_enabled", False)
    )
    
    state["medication_response"] = response
    state["response"] = response
    
    # Extract actions from actual parsed data (not hardcoded)
    actions = {
        "intent": parsed.get("intent"),  # Actual intent from LLM/parsing
        "drug": parsed.get("drug"),      # Actual drug mentioned
        "risk_level": risk                # Actual risk assessment result
    }
    
    # Extract policies that were actually applied/checked
    # Only log policies that were relevant to this interaction
    policies_applied = []
    if risk:  # Risk assessment was performed
        policies_applied.append("risk_assessment")
    if risk == "RED":  # Escalation policy was triggered
        policies_applied.append("escalate_on_red_risk")
    
    policies = {
        "policies_applied": policies_applied,
        "risk_level": risk,
        "triage_required": AGENT_POLICY.get("triage_required", False)  # From policy file
    }
    
    log_entry = {
        "ts": now_iso(),
        "agent": "MedicationEducationAgent",
        "patient_id": patient_id,
        "input": user_input,
        "intent": parsed.get("intent"),
        "risk_level": risk,
        "response": response,
        "provider": llm_provider,
        "model": llm_model,
        "latency_ms": latency_ms,  # Store latency for conversation log
        "actions": actions,
        "policies": policies
    }
    state["log_entry"] = log_entry
    log_medication(log_entry)
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

