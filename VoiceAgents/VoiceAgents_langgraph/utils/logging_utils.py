"""
Logging utilities for VoiceAgents LangGraph
Writes agent-specific logs to logs/ directory with unified schema
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from . import now_iso

# Log directory (go up two levels from utils/ to VoiceAgents_langgraph/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Agent-specific log files
APPOINTMENT_LOG = os.path.join(LOG_DIR, "appointment_agent_log.jsonl")
FOLLOWUP_LOG = os.path.join(LOG_DIR, "followup_agent_log.jsonl")
MEDICATION_LOG = os.path.join(LOG_DIR, "med_agent_log.jsonl")
CAREGIVER_LOG = os.path.join(LOG_DIR, "caregiver_summaries.jsonl")
CAREGIVER_TXT = os.path.join(LOG_DIR, "caregiver_summaries.txt")
ORCHESTRATION_LOG = os.path.join(LOG_DIR, "orchestration_log.jsonl")

# Global conversation logger (replaces TeeOutput)
_conversation_logger = None


def get_conversation_logger():
    """
    Get or create the global conversation logger.
    Configured with StreamHandler (console only - no file output).
    """
    global _conversation_logger
    
    if _conversation_logger is not None:
        return _conversation_logger
    
    # Create logger
    logger = logging.getLogger("conversation")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler (StreamHandler) - terminal output only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    _conversation_logger = logger
    return logger


def setup_console_logging():
    """
    Set up conversation logging (backward compatibility).
    Now uses Python logging module instead of TeeOutput.
    """
    get_conversation_logger()


def restore_console_logging():
    """
    Restore console logging (backward compatibility - no-op now).
    """
    pass


def _extract_action_label(actions: Optional[Dict[str, Any]], agent: Optional[str]) -> Optional[str]:
    """
    Extract a simple action label from actions dict or agent context.
    Returns short labels like: check_status, schedule, reschedule, cancel, symptom_triage, medication_info, help_message, error_handler
    """
    if not actions:
        return None
    
    # Appointment actions
    action = actions.get("action")
    if action:
        if action in ["check_status", "schedule", "reschedule", "cancel"]:
            return action
        elif action == "schedule_new":
            return "schedule"
        elif action == "general":
            return "check_status"  # Default for appointment general queries
    
    # Medication actions
    intent = actions.get("intent")
    if intent and agent == "medication":
        if intent in ["general", "info", "education"]:
            return "medication_info"
        elif intent == "side_effects":
            return "medication_info"
    
    # Followup actions
    if agent == "followup":
        triage_tier = actions.get("triage_tier")
        if triage_tier:
            return "symptom_triage"
        if actions.get("symptoms_logged"):
            return "symptom_triage"
    
    # Caregiver actions
    if agent == "caregiver":
        return "caregiver_summary"
    
    # Help actions
    if agent == "help":
        if actions.get("used_llm"):
            return "help_message"
        return "help_message"
    
    # Error
    if agent == "error":
        return "error_handler"
    
    return None


def log_turn_summary(
    timestamp: str,
    conversation_id: str,
    turn_index: int,
    role: str,
    agent: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    message: Optional[str] = None,
    actions: Optional[Dict[str, Any]] = None,
    policies: Optional[Dict[str, Any]] = None,
    used_llm: Optional[int] = None,
    latency_ms: Optional[int] = None,
    tts_used: Optional[int] = None,
    tts_backend: Optional[str] = None,
    input_channel: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log a turn summary to console (terminal) following todo.md format.
    
    For user turns: timestamp, conversation_id, role=user, message
    For assistant turns: timestamp, conversation_id, role=assistant, agent, used_llm, provider, model, latency_ms, tts_used, action
    For errors: timestamp, conversation_id, role=system, agent, level=ERROR, error
    """
    logger = get_conversation_logger()
    
    # Format timestamp to match todo.md (ISO format with Z)
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        ts_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        ts_str = timestamp
    
    if role == "user":
        # User turn format: [timestamp] | cid=... | role=user | msg="..."
        msg_preview = message[:200] + "..." if message and len(message) > 200 else (message or "")
        # Escape quotes in message
        msg_preview = msg_preview.replace('"', '\\"')
        parts = [f"[{ts_str}]", f"cid={conversation_id}", "role=user", f'msg="{msg_preview}"']
        if input_channel:
            parts.append(f"input={input_channel}")
        logger.info(" | ".join(parts))
    
    elif role == "assistant":
        # Assistant turn format: [timestamp] | cid=... | role=assistant | agent=... | used_llm=... | provider=... | model=... | latency_ms=... | tts_used=... | action=... | msg="..."
        parts = [f"[{ts_str}]", f"cid={conversation_id}", "role=assistant"]
        
        if agent:
            parts.append(f"agent={agent}")
        
        # LLM usage
        if used_llm is not None:
            parts.append(f"used_llm={used_llm}")
        elif provider and model:
            parts.append("used_llm=1")
        else:
            parts.append("used_llm=0")
        
        if provider and model:
            parts.append(f"provider={provider}")
            parts.append(f"model={model}")
        
        if latency_ms is not None:
            parts.append(f"latency_ms={latency_ms}")
        
        # TTS usage
        if tts_used is not None:
            parts.append(f"tts_used={tts_used}")
        elif tts_backend:
            parts.append("tts_used=1")
        
        if tts_backend:
            parts.append(f"tts_backend={tts_backend}")
        
        # Action label
        action_label = _extract_action_label(actions, agent)
        if action_label:
            parts.append(f"action={action_label}")
        
        # Include message text (truncated if too long)
        if message:
            msg_preview = message[:200] + "..." if len(message) > 200 else message
            msg_preview = msg_preview.replace('"', '\\"').replace('\n', ' ')  # Escape quotes and newlines
            parts.append(f'msg="{msg_preview}"')
        
        logger.info(" | ".join(parts))
    
    elif role == "system" and error:
        # Error format: [timestamp] | cid=... | role=system | agent=... | level=ERROR | error="..."
        error_msg = error.replace('"', '\\"')
        parts = [
            f"[{ts_str}]",
            f"cid={conversation_id}",
            "role=system",
            f"agent={agent or 'unknown'}",
            "level=ERROR",
            f'error="{error_msg}"'
        ]
        logger.error(" | ".join(parts))


def log_to_file(log_path: str, obj: Dict[str, Any]) -> None:
    """Write a log entry to a JSONL file"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_log(
        agent: str,
        level: str,
        message: str,
        risk: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None) -> None:
    """
    Unified log writer with consistent schema.
    
    Args:
        agent: Agent name (e.g., "appointment", "followup", "medication")
        level: Log level (e.g., "info", "warning", "error")
        message: Log message
        risk: Risk level if applicable (e.g., "RED", "ORANGE", "GREEN")
        context: Additional context dictionary
    """
    entry = {
        "timestamp": now_iso(),
        "agent": agent,
        "level": level,
        "message": message,
        "risk": risk,
        "context": context or {}
    }
    
    # Map agent names to log files
    agent_log_map = {
        "appointment": APPOINTMENT_LOG,
        "followup": FOLLOWUP_LOG,
        "medication": MEDICATION_LOG,
        "caregiver": CAREGIVER_LOG,
        "orchestration": ORCHESTRATION_LOG
    }
    
    log_path = agent_log_map.get(agent.lower(), ORCHESTRATION_LOG)
    log_to_file(log_path, entry)


def log_appointment(entry: Dict[str, Any]) -> None:
    """Log appointment agent interaction (backward compatible)"""
    # Normalize timestamp key
    if "ts" in entry and "timestamp" not in entry:
        entry["timestamp"] = entry.pop("ts")
    elif "timestamp" not in entry:
        entry["timestamp"] = now_iso()
    
    # Ensure consistent schema
    # Exclude provider/model/actions/policies - these only go to conversation_log
    excluded_fields = [
        "timestamp", "agent", "level", "message", "risk",
        "patient_id", "input", "parsed", "response",
        "provider", "model", "actions", "policies"
    ]
    normalized = {
        "timestamp": entry.get("timestamp", now_iso()),
        "agent": entry.get("agent", "appointment"),
        "level": entry.get("level", "info"),
        "message": entry.get("message", entry.get("response", "")),
        "risk": entry.get("risk"),
        "context": {
            "patient_id": entry.get("patient_id"),
            "input": entry.get("input"),
            "parsed": entry.get("parsed"),
            "response": entry.get("response"),
            **{k: v for k, v in entry.items()
               if k not in excluded_fields}
        }
    }
    log_to_file(APPOINTMENT_LOG, normalized)


def log_followup(entry: Dict[str, Any]) -> None:
    """Log follow-up agent interaction (backward compatible)"""
    # Normalize timestamp key
    if "ts" in entry and "timestamp" not in entry:
        entry["timestamp"] = entry.pop("ts")
    elif "timestamp" not in entry:
        entry["timestamp"] = now_iso()
    
    # Ensure consistent schema
    # Exclude provider/model/actions/policies - these only go to conversation_log
    excluded_fields = [
        "timestamp", "agent", "level", "message", "risk",
        "triage", "patient_id", "input", "symptom",
        "severity", "response", "provider", "model", "actions", "policies"
    ]
    normalized = {
        "timestamp": entry.get("timestamp", now_iso()),
        "agent": entry.get("agent", "followup"),
        "level": entry.get("level", "info"),
        "message": entry.get("message", entry.get("response", "")),
        "risk": entry.get("risk", entry.get("triage")),
        "context": {
            "patient_id": entry.get("patient_id"),
            "input": entry.get("input"),
            "symptom": entry.get("symptom"),
            "severity": entry.get("severity"),
            "response": entry.get("response"),
            **{k: v for k, v in entry.items()
               if k not in excluded_fields}
        }
    }
    log_to_file(FOLLOWUP_LOG, normalized)


def log_medication(entry: Dict[str, Any]) -> None:
    """Log medication agent interaction (backward compatible)"""
    # Normalize timestamp key
    if "ts" in entry and "timestamp" not in entry:
        entry["timestamp"] = entry.pop("ts")
    elif "timestamp" not in entry:
        entry["timestamp"] = now_iso()
    
    # Ensure consistent schema
    # Exclude provider/model/actions/policies - these only go to conversation_log
    excluded_fields = [
        "timestamp", "agent", "level", "message", "risk",
        "patient_id", "input", "intent", "drug", "response",
        "provider", "model", "actions", "policies"
    ]
    normalized = {
        "timestamp": entry.get("timestamp", now_iso()),
        "agent": entry.get("agent", "medication"),
        "level": entry.get("level", "info"),
        "message": entry.get("message", entry.get("response", "")),
        "risk": entry.get("risk"),
        "context": {
            "patient_id": entry.get("patient_id"),
            "input": entry.get("input"),
            "intent": entry.get("intent"),
            "drug": entry.get("drug"),
            "response": entry.get("response"),
            **{k: v for k, v in entry.items()
               if k not in excluded_fields}
        }
    }
    log_to_file(MEDICATION_LOG, normalized)


def log_caregiver(entry: Dict[str, Any], write_txt: bool = True) -> None:
    """Log caregiver agent interaction (backward compatible)"""
    # Normalize timestamp key
    if "ts" in entry and "timestamp" not in entry:
        entry["timestamp"] = entry.pop("ts")
    elif "timestamp" not in entry:
        entry["timestamp"] = now_iso()
    
    # Ensure consistent schema
    # Exclude provider/model/actions/policies - these only go to conversation_log
    excluded_fields = [
        "timestamp", "agent", "level", "message", "risk",
        "patient_id", "caregiver_id", "summary",
        "provider", "model", "actions", "policies"
    ]
    normalized = {
        "timestamp": entry.get("timestamp", now_iso()),
        "agent": entry.get("agent", "caregiver"),
        "level": entry.get("level", "info"),
        "message": entry.get("message", "Caregiver summary generated"),
        "risk": entry.get("risk"),
        "context": {
            "patient_id": entry.get("patient_id"),
            "caregiver_id": entry.get("caregiver_id"),
            "summary": entry.get("summary"),
            **{k: v for k, v in entry.items()
               if k not in excluded_fields}
        }
    }
    log_to_file(CAREGIVER_LOG, normalized)
    
    # Also write to text file if summary_text exists
    if write_txt and "summary_text" in entry:
        with open(CAREGIVER_TXT, "a", encoding="utf-8") as f:
            f.write(entry["summary_text"] + "\n\n")


def log_orchestration(entry: Dict[str, Any]) -> None:
    """Log orchestration/routing interaction (backward compatible)"""
    # Normalize timestamp key
    if "ts" in entry and "timestamp" not in entry:
        entry["timestamp"] = entry.pop("ts")
    elif "timestamp" not in entry:
        entry["timestamp"] = now_iso()
    
    # Ensure consistent schema
    # Exclude provider/model/actions/policies - these only go to conversation_log
    excluded_fields = [
        "timestamp", "agent", "level", "message", "risk",
        "patient_id", "input", "intent",
        "provider", "model", "actions", "policies"
    ]
    normalized = {
        "timestamp": entry.get("timestamp", now_iso()),
        "agent": entry.get("agent", "orchestration"),
        "level": entry.get("level", "info"),
        "message": entry.get("message", entry.get("intent", "")),
        "risk": entry.get("risk"),
        "context": {
            "patient_id": entry.get("patient_id"),
            "input": entry.get("input"),
            "intent": entry.get("intent"),
            **{k: v for k, v in entry.items()
               if k not in excluded_fields}
        }
    }
    log_to_file(ORCHESTRATION_LOG, normalized)
