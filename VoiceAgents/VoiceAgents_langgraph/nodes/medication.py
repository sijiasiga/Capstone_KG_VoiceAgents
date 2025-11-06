"""
Medication Agent Node - LangGraph implementation
"""
import json
import os
import sys
from typing import Dict, Optional
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
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    print(f"[Policy] Medication Agent loaded: scope=[{scope_str}], triage={AGENT_POLICY.get('triage_required', False)}")

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
KNOWLEDGE_PATH = os.path.join(DATA_DIR, "drug_knowledge.csv")
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def llm_parse_query(user_text: str) -> Dict:
    """Use LLM to extract intent, drugs, and symptoms."""
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
        return {"intent": intent, "language": "en"}
    
    sys = {"role": "system", "content": "Return ONLY valid JSON. No prose."}
    user = {
        "role": "user",
        "content": f"""
Parse this medication question. Return JSON with:
- intent: one of ["missed_dose","double_dose","side_effect","interaction_check","instruction","contraindication","general"]
- drugs_mentioned: [{{"raw":string,"norm_name":string|null}}]
- language: "en"

Question: "{user_text}"
""",
    }
    try:
        messages = [sys, user]
        content = chat_completion(messages=messages, temperature=0, model=get_default_model())
        if not content:
            return {"intent": "general", "language": "en"}
        return json.loads(content.strip())
    except Exception:
        return {"intent": "general", "language": "en"}


def llm_score_risk(parsed: Dict) -> str:
    """Return RED / ORANGE / GREEN risk."""
    if not USE_LLM:
        intent = parsed.get("intent")
        if intent == "double_dose":
            return "RED"
        if intent in ["interaction_check", "missed_dose"]:
            return "ORANGE"
        return "GREEN"
    
    messages = [
        {"role": "system", "content": "Return ONLY a single word: RED, ORANGE, or GREEN."},
        {"role": "user", "content": json.dumps(parsed, ensure_ascii=False)}
    ]
    try:
        content = chat_completion(messages=messages, temperature=0, model=get_default_model())
        if not content:
            return "GREEN"
        return content.strip().upper()
    except Exception:
        return "GREEN"


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
    
    def handle(self, patient_id: str, user_text: str, use_voice: bool = False) -> str:
        patient = self.db.get_patient(patient_id)
        if not patient:
            return "Patient not found."
        
        parsed = llm_parse_query(user_text)
        intent = parsed.get("intent", "general")
        
        prescriptions = self.db.get_prescriptions(patient_id)
        if not prescriptions:
            return "No prescriptions found for this patient."
        
        risk = llm_score_risk(parsed)
        
        responses = []
        for p in prescriptions:
            info = self._get_drug_info(p["drug_name"])
            if not info:
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
                responses.append(f"{p['drug_name']} is used for {p['condition']} ({info['drug_class']} class).")
        
        if intent == "interaction_check" and len(responses) > 1:
            responses.insert(0, "You're taking multiple medications. Here are the interaction warnings:")
        
        if not responses:
            responses.append("I could not interpret your medication question clearly.")
        
        combined = " ".join(responses)
        if risk == "RED":
            combined = "[HIGH RISK] Please seek immediate medical care. " + combined
        elif risk == "ORANGE":
            combined = "[ALERT] Please contact your clinician soon. " + combined
        
        return combined


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
    response = service.handle(patient_id, user_input, use_voice=state.get("voice_enabled", False))
    
    state["medication_response"] = response
    state["response"] = response
    
    # Log entry
    parsed = llm_parse_query(user_input)
    risk = llm_score_risk(parsed)
    
    log_entry = {
        "ts": now_iso(),
        "agent": "MedicationEducationAgent",
        "patient_id": patient_id,
        "input": user_input,
        "intent": parsed.get("intent"),
        "risk_level": risk,
        "response": response,
    }
    state["log_entry"] = log_entry
    log_medication(log_entry)
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

