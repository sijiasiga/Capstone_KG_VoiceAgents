"""
Logging utilities for VoiceAgents LangGraph
Writes agent-specific logs to logs/ directory with unified schema
"""
import os
import json
from typing import Dict, Any, Optional
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
               if k not in ["timestamp", "agent", "level", "message", "risk",
                           "patient_id", "input", "parsed", "response"]}
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
               if k not in ["timestamp", "agent", "level", "message", "risk",
                           "triage", "patient_id", "input", "symptom",
                           "severity", "response"]}
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
               if k not in ["timestamp", "agent", "level", "message", "risk",
                           "patient_id", "input", "intent", "drug", "response"]}
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
               if k not in ["timestamp", "agent", "level", "message", "risk",
                           "patient_id", "caregiver_id", "summary"]}
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
               if k not in ["timestamp", "agent", "level", "message", "risk",
                           "patient_id", "input", "intent"]}
        }
    }
    log_to_file(ORCHESTRATION_LOG, normalized)

