"""
Follow-Up Agent Node - LangGraph implementation
"""
import json
import csv
import os
import re
from typing import Dict, Optional, List, Tuple
from ..state import VoiceAgentState
from ..utils import now_iso, say
from ..utils.llm_provider import chat_completion, USE_LLM, get_default_model
from ..utils.logging_utils import log_followup

# Use local database
from ..database import DatabaseService

# Load agent-specific policy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "followup_policy.json")
AGENT_POLICY = {}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r") as f:
        AGENT_POLICY = json.load(f)
    # Log policy summary on startup
    from ..utils.logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    logger.info(f"[Policy] Followup Agent loaded: scope=[{scope_str}], triage={AGENT_POLICY.get('triage_required', False)}")

# Symptom codebook - use local data folder
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CODEBOOK_CSV = os.path.join(DATA_DIR, "symptom_codes.csv")


def load_symptom_codebook() -> List[Dict]:
    items = []
    if os.path.exists(CODEBOOK_CSV):
        with open(CODEBOOK_CSV, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                items.append(row)
    return items


CODEBOOK = load_symptom_codebook()


def normalize_symptom(text: str) -> Dict:
    """Return {'canonical':str,'snomed':str} or default."""
    t = text.lower().strip()
    for row in CODEBOOK:
        if row["term"].lower() in t:
            return {"canonical": row["canonical"], "snomed": row["snomed_code"]}
    # LLM fallback
    if USE_LLM:
        messages = [
            {"role": "system", "content": "Return ONLY valid JSON with fields: canonical, snomed"},
            {"role": "user", "content": f"Map this symptom phrase to a canonical term and SNOMED code if possible, else guess canonical='other' and snomed='NA'. Phrase: {text}"}
        ]
        try:
            result = chat_completion(messages=messages, temperature=0, model=get_default_model())
            if not result:
                return {"canonical": "other", "snomed": "NA"}
            # Handle tuple return: (text, provider, model)
            content = result[0] if isinstance(result, tuple) else result
            if not content:
                return {"canonical": "other", "snomed": "NA"}
            j = json.loads(content.strip())
            if isinstance(j, dict) and j.get("canonical"):
                return {"canonical": j.get("canonical", "other"), "snomed": j.get("snomed", "NA")}
        except Exception:
            pass
    return {"canonical": "other", "snomed": "NA"}


def llm_parse_symptom(user_text: str) -> Dict:
    """Extract symptom phrase + severity_0_10."""
    if not USE_LLM:
        sev = 0
        for k in range(10, -1, -1):
            if f"{k}/10" in user_text or f"{k} out of 10" in user_text:
                sev = k
                break
        return {"symptom_text": user_text, "severity_0_10": sev}
    
    messages = [
        {"role": "system", "content": "Return ONLY valid JSON with fields: symptom_text, severity_0_10 (0-10 or null)."},
        {"role": "user", "content": f"Extract symptom and optional numeric severity from: {user_text}"}
    ]
    try:
        result = chat_completion(messages=messages, temperature=0, model=get_default_model())
        if not result:
            return {"symptom_text": user_text, "severity_0_10": None}
        # Handle tuple return: (text, provider, model)
        content = result[0] if isinstance(result, tuple) else result
        if not content:
            return {"symptom_text": user_text, "severity_0_10": None}
        return json.loads(content.strip())
    except Exception:
        return {"symptom_text": user_text, "severity_0_10": None}


RED_SEVERITY = 8
REPEAT_WINDOW_DAYS = 7
REPEAT_THRESHOLD = 2


# Load triage flags from policy file
def load_triage_flags():
    """Load RED and ORANGE triage flags from policy file."""
    red_flags = AGENT_POLICY.get("red_flags", [])
    orange_flags = AGENT_POLICY.get("orange_flags", [])
    
    # Convert range arrays to tuples for Python compatibility
    for flag in orange_flags:
        if "range" in flag and isinstance(flag["range"], list):
            flag["range"] = tuple(flag["range"])
    
    return red_flags, orange_flags


# Initialize triage flags after policy is loaded
TRIAGE_RED_FLAGS, TRIAGE_ORANGE_FLAGS = load_triage_flags()


def parse_fever_value(text: str) -> Optional[float]:
    """Parse numeric fever value from user input (e.g., 'fever of 103', 'fever is 100 degrees')."""
    text_lower = text.lower()
    
    # Pattern 1: "fever of 103", "fever of 103 degrees", "fever is 100"
    patterns = [
        r'fever\s+(?:of|is|at)\s+(\d+(?:\.\d+)?)\s*(?:degrees?|°f?)?',
        r'(\d+(?:\.\d+)?)\s*(?:degrees?|°f?)\s+(?:fever|temperature)',
        r'fever\s+(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*fever'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                value = float(match.group(1))
                # Reasonable fever range: 95-110°F
                if 95.0 <= value <= 110.0:
                    return value
            except (ValueError, IndexError):
                continue
    
    return None


def check_symptom_triage(symptoms: List[str], severity: Optional[int], text_lower: str, fever_value: Optional[float] = None) -> Tuple[str, List[str]]:
    """Check symptoms against RED/ORANGE flags. Returns (tier, matched_flags)."""
    if not symptoms:
        return "GREEN", []
    
    text_blob = " ".join([s.lower() for s in symptoms])
    text_blob += " " + text_lower  # Include full text for pattern matching
    
    # Check RED flags
    for rule in TRIAGE_RED_FLAGS:
        name, patt, thr = rule["name"], rule["pattern"], rule.get("threshold")
        if any(p in text_blob for p in patt):
            if name == "fever_high" and thr is not None:
                # Check fever threshold: >= 101.5°F is RED
                if fever_value is not None and fever_value >= thr:
                    return "RED", [name]
                # If fever mentioned but value not parsed, skip (don't assume)
                continue
            elif name == "severe_pain" and severity is not None and thr is not None:
                if severity >= thr:
                    return "RED", [name]
            elif name not in ["fever_high", "severe_pain"]:
                return "RED", [name]
    
    # Check ORANGE flags
    for rule in TRIAGE_ORANGE_FLAGS:
        name, patt = rule["name"], rule["pattern"]
        rng = rule.get("range")
        thr = rule.get("threshold")
        if any(p in text_blob for p in patt):
            if name == "fever_low" and rng is not None:
                # Check fever range: 99.5-101.4°F is ORANGE
                if fever_value is not None:
                    low, high = rng
                    if low <= fever_value <= high:
                        return "ORANGE", [name]
                # If fever mentioned but value not parsed, skip
                continue
            elif rng and severity is not None and name == "moderate_pain":
                low, high = rng
                if low <= severity <= high:
                    return "ORANGE", [name]
            elif name == "dizziness" or name in ["wound_redness", "hyperglycemia"]:
                return "ORANGE", [name]
    
    return "GREEN", []


def evaluate_alert(db: DatabaseService, patient_id: str, canonical_symptom: str, severity: Optional[int]) -> Dict:
    logs = db.get_symptom_logs_window(patient_id, canonical_symptom, days=REPEAT_WINDOW_DAYS)
    count_recent = len(logs)
    is_repeat = count_recent >= REPEAT_THRESHOLD - 1
    is_severe = (severity is not None and severity >= RED_SEVERITY)
    alert = bool(is_severe or is_repeat)
    tier = "RED" if is_severe else ("ORANGE" if is_repeat else "GREEN")
    return {"alert": alert, "tier": tier, "recent_count": count_recent}


def followup_node(state: VoiceAgentState) -> VoiceAgentState:
    """Follow-up agent node"""
    user_input = state.get("user_input", "")
    patient_id = state.get("patient_id")
    
    if not patient_id:
        response = "Please provide your 8-digit patient ID to report symptoms."
        state["followup_response"] = response
        state["response"] = response
        return state
    
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
        fever_temp = triage_context.get("fever_temperature") if triage_context else None
        fever_str = f"{fever_temp:.1f}°F" if fever_temp else "high fever"
        
        # Determine escalation path
        if has_flu_symptoms:
            # Flu symptoms + high fever → Nurse callback (not ER)
            escalation_path = "warm_transfer_rn"
            triage_tier = "ORANGE"  # Downgrade from RED to ORANGE due to flu context
            response = f"Thank you for answering those questions. Based on your responses, you have flu-like symptoms along with your {fever_str} fever. This combination is often expected with the flu and typically doesn't require emergency care. I'm connecting you with a nurse right now who can provide guidance and help determine if you need to be seen sooner."
        else:
            # High fever without flu symptoms → ER (more serious)
            escalation_path = "er"
            triage_tier = "RED"
            response = f"Thank you for answering those questions. Based on your responses, your {fever_str} fever without flu-like symptoms could indicate something more serious. Please go to the nearest emergency department right away. I'm also alerting the on-call nurse about this."
        
        # Update state and clear probing phase
        state["triage_phase"] = None
        state["triage_context"] = None
        state["escalation_path"] = escalation_path
        state["followup_response"] = response
        state["response"] = response
        
        # Separate policy recording structure
        policies = {
            "triage_classification": {
                "triage_tier": triage_tier,
                "triage_required": AGENT_POLICY.get("triage_required", False)
            },
            "flag_matching": {
                "matched_flags": ["fever_high"]
            },
            "escalation_policy": {
                "escalation_path": escalation_path,
                "escalated": True
            }
        }
        
        # Log the decision
        log_entry = {
            "ts": now_iso(),
            "agent": "FollowUpAgent",
            "patient_id": patient_id,
            "input": user_input,
            "response": response,
            "triage_phase": "fever_probe_completed",
            "escalation_path": escalation_path,
            "triage_tier": triage_tier,
            "matched_flags": ["fever_high"],
            "fever_value": fever_temp,
            "triage_context": triage_context,
            "policies": policies
        }
        state["log_entry"] = log_entry
        log_followup(log_entry)
        
        if state.get("voice_enabled", False):
            say(response, voice=True)
        
        return state
    
    db = DatabaseService()
    text_lower = user_input.lower()
    
    # Extract symptoms and severity using LLM for better detection
    symptoms = []
    severity = None
    
    # Extract severity first
    m = re.search(r'(\d+)\s*(?:out\s*of\s*10|/10)?', text_lower)
    if m:
        try:
            val = int(m.group(1))
            if 0 <= val <= 10:
                severity = val
        except Exception:
            pass
    
    # Extract fever value (numeric temperature)
    fever_value = parse_fever_value(user_input)
    
    # Use LLM to extract symptoms if available
    llm_provider = None
    llm_model = None
    latency_ms = None
    if USE_LLM:
        symptom_extraction_prompt = f"""Extract all symptoms mentioned in this text. Return ONLY a JSON array of symptom names.
Text: "{user_input}"
Examples: 
- "tightness in my chest" → ["chest tightness"]
- "I feel dizzy and tired" → ["dizziness", "fatigue"]
- "pain in my chest" → ["chest pain"]
- "I've been feeling some tightness in my chest" → ["chest tightness"]
Return: ["symptom1", "symptom2", ...] or [] if no symptoms."""
        try:
            messages = [
                {"role": "system", "content": "Return ONLY valid JSON array. No prose."},
                {"role": "user", "content": symptom_extraction_prompt}
            ]
            result = chat_completion(messages=messages, temperature=0, model=get_default_model())
            if result:
                # Handle tuple return: (text, provider, model, latency_ms) or (text, provider, model)
                if isinstance(result, tuple):
                    if len(result) == 4:
                        content, llm_provider, llm_model, latency_ms = result
                    else:
                        content, llm_provider, llm_model = result[:3]
                        latency_ms = result[3] if len(result) > 3 else None
                else:
                    content = result
                    llm_provider = None
                    llm_model = None
                    latency_ms = None
                if content:
                    try:
                        llm_symptoms = json.loads(content.strip())
                        if isinstance(llm_symptoms, list):
                            # Normalize symptom names for better matching
                            normalized = []
                            for s in llm_symptoms:
                                s_lower = s.lower()
                                # Normalize common variations
                                if "chest" in s_lower and "tight" in s_lower:
                                    normalized.append("chest tightness")
                                elif "chest" in s_lower and "pain" in s_lower:
                                    normalized.append("chest pain")
                                else:
                                    normalized.append(s_lower)
                            symptoms.extend(normalized)
                    except Exception:
                        pass
        except Exception:
            pass
    
    # Fallback: keyword-based detection (expanded list, sorted by length descending to catch phrases first)
    if not symptoms:
        symptom_keywords = [
            "tightness in my chest", "pain in my chest", "chest tightness", "chest pain",
            "shortness of breath", "trouble breathing", "short of breath",
            "slurred speech", "dizziness", "breathless", "headache",
            "pain", "fever", "dizzy", "cough", "fatigue", "tired", 
            "tightness", "nausea", "ache", "swelling", "redness", 
            "weakness", "numbness", "fainted", "syncope"
        ]
        for kw in symptom_keywords:
            if kw in text_lower:
                # Special handling: if "tightness" is found, check if it's chest-related
                if kw == "tightness" and "chest" in text_lower:
                    symptoms.append("chest tightness")
                else:
                    symptoms.append(kw)
                break  # Found at least one, that's enough
    
    if not symptoms:
        # More conversational response
        response = "I'd like to help you with your symptoms. Could you tell me more specifically what you're experiencing? For example, are you feeling pain, dizziness, shortness of breath, or something else?"
        state["followup_response"] = response
        state["response"] = response
        return state
    
    # Check triage flags FIRST (before logging)
    triage_tier, matched_flags = check_symptom_triage(symptoms, severity, text_lower, fever_value)
    
    # Log symptoms
    db.add_symptom_log(patient_id, symptoms, severity)
    
    # Get recent history
    recent = db.get_recent_symptoms(patient_id, days=7)
    unique_symptoms = list({s["symptom"] for s in recent})
    
    # Construct response based on triage tier
    symptom_str = ", ".join(symptoms)
    
    # RED FLAG - Serious symptoms
    if triage_tier == "RED":
        # Check if this is a high fever case that needs probing
        is_fever_high = "fever_high" in matched_flags and fever_value is not None and fever_value >= 101.5
        if is_fever_high:
            # Start fever probing phase instead of immediate ER
            state["triage_phase"] = "fever_probe"
            state["triage_context"] = {
                "initial_symptoms": symptoms,
                "fever_temperature": fever_value,
                "user_input": user_input,
                "originating_agent": "followup"  # Track which agent started the probe
            }
            
            # Ask probing questions
            response = "I understand you're experiencing a high fever. To help determine the best course of action, I need to ask a few quick questions: "
            response += "Do you have any flu-like symptoms, such as body aches, cough, or runny nose? "
            response += "When did the fever start? "
            response += "And have you taken any fever-reducing medication like Tylenol or Advil?"
            
            state["followup_response"] = response
            state["response"] = response
            
            # Separate policy recording structure
            policies = {
                "triage_classification": {
                    "triage_tier": "RED",
                    "triage_required": AGENT_POLICY.get("triage_required", False)
                },
                "flag_matching": {
                    "matched_flags": matched_flags
                },
                "escalation_policy": {
                    "escalation_path": "fever_probe_started",
                    "escalated": False  # Not escalated yet, probing first
                }
            }
            
            log_entry = {
                "ts": now_iso(),
                "agent": "FollowUpAgent",
                "patient_id": patient_id,
                "input": user_input,
                "symptoms": symptoms,
                "severity": severity,
                "fever_value": fever_value,
                "triage_tier": "RED",
                "matched_flags": matched_flags,
                "response": response,
                "provider": llm_provider,
                "model": llm_model,
                "latency_ms": latency_ms,
                "triage_phase": "fever_probe_started",
                "actions": {
                    "symptoms_logged": symptoms,
                    "severity": severity,
                    "triage_tier": "RED"
                },
                "policies": policies
            }
            state["log_entry"] = log_entry
            log_followup(log_entry)
            
            if state.get("voice_enabled", False):
                say(response, voice=True)
            
            return state
        
        # All other RED cases: immediate ER (unchanged behavior)
        response = f"I understand you're experiencing {symptom_str}."
        if severity is not None:
            response += f" With a severity of {severity} out of 10,"
            response += " this could be a serious symptom. Please go to the nearest emergency department immediately or call 911 if this is an emergency. I'm also alerting your healthcare provider right away."
        else:
            response += " this could be a serious symptom. Please go to the nearest emergency department immediately or call 911 if this is an emergency. I'm also alerting your healthcare provider right away."
        state["followup_response"] = response
        state["response"] = response
        
        # Extract actions and policies for RED tier
        actions = {
            "symptoms_logged": symptoms,
            "severity": severity,
            "triage_tier": triage_tier
        }
        
        # Separate policy recording structure
        policies = {
            "triage_classification": {
                "triage_tier": triage_tier,
                "triage_required": AGENT_POLICY.get("triage_required", False)
            },
            "flag_matching": {
                "matched_flags": matched_flags
            },
            "escalation_policy": {
                "escalation_path": "er",
                "escalated": True
            }
        }
        
        log_entry = {
            "ts": now_iso(),
            "agent": "FollowUpAgent",
            "patient_id": patient_id,
            "input": user_input,
            "symptoms": symptoms,
            "severity": severity,
            "fever_value": fever_value,  # Include parsed fever value
            "triage_tier": "RED",
            "matched_flags": matched_flags,
            "response": response,
            "provider": llm_provider,
            "model": llm_model,
            "latency_ms": latency_ms,  # Store latency for conversation log
            "actions": actions,
            "policies": policies
        }
        state["log_entry"] = log_entry
        log_followup(log_entry)
        if state.get("voice_enabled", False):
            say(response, voice=True)
        return state
    
    # ORANGE FLAG - Concerning symptoms
    if triage_tier == "ORANGE":
        response = f"I've noted that you're experiencing {symptom_str}."
        # Special handling for low-moderate fever
        if "fever_low" in matched_flags and fever_value is not None:
            response += f" With a fever of {fever_value:.1f}°F, I'm going to have a nurse call you today to review your symptoms and discuss next steps. They can help determine if you need to be seen sooner. In the meantime, monitor your temperature and watch for any worsening symptoms."
        elif severity is not None:
            response += f" With a severity of {severity} out of 10,"
            response += " I'm going to have a nurse call you today to review your symptoms and discuss next steps. They can help determine if you need to be seen sooner."
        else:
            response += " I'm going to have a nurse call you today to review your symptoms and discuss next steps. They can help determine if you need to be seen sooner."
        if len(unique_symptoms) > 1:
            response += f" I also notice you reported {', '.join(unique_symptoms[:-1])} earlier this week."
        state["followup_response"] = response
        state["response"] = response
        
        # Extract actions and policies for ORANGE tier
        actions = {
            "symptoms_logged": symptoms,
            "severity": severity,
            "triage_tier": triage_tier
        }
        
        # Separate policy recording structure
        policies = {
            "triage_classification": {
                "triage_tier": triage_tier,
                "triage_required": AGENT_POLICY.get("triage_required", False)
            },
            "flag_matching": {
                "matched_flags": matched_flags
            },
            "escalation_policy": {
                "escalation_path": "nurse_callback",
                "escalated": True
            }
        }
        
        log_entry = {
            "ts": now_iso(),
            "agent": "FollowUpAgent",
            "patient_id": patient_id,
            "input": user_input,
            "symptoms": symptoms,
            "severity": severity,
            "fever_value": fever_value,  # Include parsed fever value
            "triage_tier": "ORANGE",
            "matched_flags": matched_flags,
            "response": response,
            "provider": llm_provider,
            "model": llm_model,
            "latency_ms": latency_ms,  # Store latency for conversation log
            "actions": actions,
            "policies": policies
        }
        state["log_entry"] = log_entry
        log_followup(log_entry)
        if state.get("voice_enabled", False):
            say(response, voice=True)
        return state
    
    # GREEN - Normal symptoms
    if len(symptoms) == 1:
        response = f"I've logged that you're experiencing {symptom_str}"
    else:
        response = f"I've logged that you're experiencing {symptom_str}"
    
    if severity is not None:
        response += f" with a severity of {severity} out of 10"
    response += "."
    
    if len(unique_symptoms) > 1:
        response += f" I notice you also reported {', '.join(unique_symptoms[:-1])} earlier this week."
    
    if severity and severity >= 7:
        response += " Given the high severity, I'm going to notify your healthcare provider right away. Please seek immediate medical attention if your symptoms worsen."
    elif severity and severity >= 5:
        response += " I'll make sure your provider is aware of this. Is there anything else concerning you today?"
    else:
        response += " I've added this to your medical record, and your provider will review it during your next appointment."
    
    state["followup_response"] = response
    state["response"] = response
    
    # Extract actions from actual execution (what actually happened)
    actions = {
        "symptoms_logged": symptoms,      # Actual symptoms that were logged
        "severity": severity,            # Actual severity score
        "triage_tier": triage_tier       # Actual triage classification
    }
    
    # Separate policy recording structure
    policies = {
        "triage_classification": {
            "triage_tier": triage_tier,
            "triage_required": AGENT_POLICY.get("triage_required", False)
        },
        "flag_matching": {
            "matched_flags": matched_flags
        },
        "escalation_policy": {
            "escalation_path": None,  # GREEN tier - no escalation
            "escalated": False
        }
    }
    
    # Log entry (triage_tier already set above in RED/ORANGE cases)
    log_entry = {
        "ts": now_iso(),
        "agent": "FollowUpAgent",
        "patient_id": patient_id,
        "input": user_input,
        "symptoms": symptoms,
        "severity": severity,
        "fever_value": fever_value,  # Include parsed fever value
        "triage_tier": triage_tier,
        "matched_flags": matched_flags,
        "response": response,
        "provider": llm_provider,
        "model": llm_model,
        "latency_ms": latency_ms,  # Store latency for conversation log
        "actions": actions,
        "policies": policies
    }
    state["log_entry"] = log_entry
    log_followup(log_entry)
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

