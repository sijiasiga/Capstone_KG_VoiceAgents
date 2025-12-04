"""
Routing Node - Determines intent and routes to appropriate agent
"""
import json
import re
from typing import Literal
from ..state import VoiceAgentState
from ..utils.llm_provider import chat_completion, USE_LLM, get_default_model

INTENT_LABELS = ["appointment", "followup", "medication", "caregiver", "help"]


def parse_intent_rules(text: str) -> dict:
    """Rule-based intent parsing fallback"""
    t = text.lower()
    intent = "help"
    
    # Priority: appointment keywords first (since scheduling can include symptoms)
    if any(k in t for k in ["appointment", "reschedule", "schedule", "cancel", "doctor", "visit", 
                            "check my appointment", "book", "next tuesday", "next week", "follow-up appointment"]):
        intent = "appointment"
    elif any(k in t for k in [
        "breathless", "shortness of breath", "symptom", "dizzy", "dizziness",
        "pain", "fever", "tired", "fatigue", "weakness", "chest pain", "tightness", 
        "feeling", "hurt", "ache", "nausea", "cough"
    ]):
        # Only route to followup if NOT about scheduling
        if not any(k in t for k in ["schedule", "appointment", "book", "reschedule"]):
            intent = "followup"
        else:
            intent = "appointment"  # If mentions both, prioritize appointment
    elif any(k in t for k in ["med", "medication", "pill", "dose", "dosage", "prescription", "taking", "side effect", "missed dose", "take with food", "what medication", "my medication"]):
        intent = "medication"
    elif any(k in t for k in ["caregiver", "weekly summary", "check on them", "update for parent", "mother", "father"]):
        intent = "caregiver"
    
    pid = None
    m = re.search(r"\b(\d{8})\b", text)
    if m:
        pid = m.group(1)
    
    return {"intent": intent, "patient_id": pid}


def parse_intent_llm(text: str) -> dict:
    """Use LLM to classify user intent"""
    if not USE_LLM:
        return parse_intent_rules(text)
    
    SYSTEM_PROMPT = """
    You are a routing assistant for a healthcare voice triage system.
    Classify this patient message into one of:
    appointment | followup | medication | caregiver | help
    
    IMPORTANT ROUTING RULES:
    - If the message mentions scheduling, booking, rescheduling, or checking appointments → "appointment"
    - If the message only reports symptoms/feelings without scheduling → "followup"
    - If both are mentioned, prioritize "appointment" (scheduling takes precedence)
    - "feeling" alone doesn't mean followup - check if they're scheduling or just reporting
    
    Extract any 8-digit patient ID if present.
    Reply only in JSON like:
    {"intent": "appointment", "patient_id": "10004235"}
    """
    
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": text}
        ]
        result = chat_completion(messages=messages, temperature=0, model=get_default_model())
        if not result:
            return parse_intent_rules(text)
        # Handle tuple return: (text, provider, model)
        if isinstance(result, tuple):
            raw, provider, model = result
        else:
            raw = result
            provider = None
            model = None
        if not raw:
            return parse_intent_rules(text)
        out = json.loads(raw.strip())
        # Store provider/model info in the result for potential logging
        # (Note: routing node doesn't set log_entry, but this info could be used if needed)
        intent = (out.get("intent") or "help").lower()
        if intent not in INTENT_LABELS:
            intent = "help"
        
        pid = out.get("patient_id")
        
        if intent == "help":
            rule_fallback = parse_intent_rules(text)
            return rule_fallback
        
        return {"intent": intent, "patient_id": pid}
    except Exception:
        return parse_intent_rules(text)


def route_node(state: VoiceAgentState) -> VoiceAgentState:
    """Route node - parses intent and extracts patient ID"""
    user_text = state.get("user_input", "")
    
    # Parse intent
    parsed = parse_intent_llm(user_text)
    intent = parsed.get("intent", "help")
    patient_id = parsed.get("patient_id") or state.get("patient_id")
    
    # Update state
    state["intent"] = intent
    state["patient_id"] = patient_id
    
    return state

