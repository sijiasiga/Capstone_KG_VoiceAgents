"""
Logging utilities for VoiceAgents LangGraph
Writes agent-specific logs to logs/ directory
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


def log_appointment(entry: Dict[str, Any]) -> None:
    """Log appointment agent interaction"""
    if "ts" not in entry:
        entry["ts"] = now_iso()
    log_to_file(APPOINTMENT_LOG, entry)


def log_followup(entry: Dict[str, Any]) -> None:
    """Log follow-up agent interaction"""
    if "ts" not in entry:
        entry["ts"] = now_iso()
    log_to_file(FOLLOWUP_LOG, entry)


def log_medication(entry: Dict[str, Any]) -> None:
    """Log medication agent interaction"""
    if "ts" not in entry:
        entry["ts"] = now_iso()
    log_to_file(MEDICATION_LOG, entry)


def log_caregiver(entry: Dict[str, Any], write_txt: bool = True) -> None:
    """Log caregiver agent interaction"""
    if "ts" not in entry:
        entry["ts"] = now_iso()
    log_to_file(CAREGIVER_LOG, entry)
    
    # Also write to text file if summary_text exists
    if write_txt and "summary_text" in entry:
        with open(CAREGIVER_TXT, "a", encoding="utf-8") as f:
            f.write(entry["summary_text"] + "\n\n")


def log_orchestration(entry: Dict[str, Any]) -> None:
    """Log orchestration/routing interaction"""
    if "ts" not in entry:
        entry["ts"] = now_iso()
    log_to_file(ORCHESTRATION_LOG, entry)

