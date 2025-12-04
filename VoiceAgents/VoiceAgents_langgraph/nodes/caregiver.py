"""
Caregiver Agent Node - LangGraph implementation
"""
import os
import sys
import json
from typing import Dict, Optional, List, Any
from ..state import VoiceAgentState
from ..utils import now_iso, say
from ..utils.logging_utils import log_caregiver

# Use local database
from ..database import DatabaseService

# Load agent-specific policy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "caregiver_policy.json")
AGENT_POLICY = {}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r") as f:
        AGENT_POLICY = json.load(f)
    # Log policy summary on startup
    from ..utils.logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    restrictions_str = ", ".join(AGENT_POLICY.get("restrictions", []))
    logger.info(f"[Policy] Caregiver Agent loaded: scope=[{scope_str}], restrictions=[{restrictions_str}]")


def score_risk(avg_sev: float, missed: int) -> str:
    """Simple heuristic for overall patient risk."""
    if avg_sev >= 7 or missed >= 3:
        return "HIGH"
    if avg_sev >= 4 or missed >= 1:
        return "MODERATE"
    return "LOW"


class CaregiverService:
    def __init__(self):
        self.db = DatabaseService()
    
    def summarize_one(self, patient_id: str, days: int = 7) -> Optional[Dict[str, Any]]:
        patient = self.db.get_patient(patient_id)
        if not patient:
            return None
        
        cg_id = patient.get("primary_caregiver_id")
        caregivers_df = self.db.caregivers
        if caregivers_df.empty or str(cg_id) not in caregivers_df["caregiver_id"].astype(str).values:
            return None
        
        cg = caregivers_df[caregivers_df["caregiver_id"].astype(str) == str(cg_id)].iloc[0].to_dict()
        if str(cg.get("consent_on_file", "")).strip().lower() not in ("true", "1", "yes"):
            return None
        
        # Data aggregation
        trends = self.db.get_symptom_trends(patient_id, days)
        meds = self.db.get_prescriptions(patient_id)
        
        # Medication adherence summary
        med_logs_path = os.path.join(self.db.data_dir, "med_logs.csv")
        missed = 0
        taken = 0
        if os.path.exists(med_logs_path):
            import pandas as pd
            df = pd.read_csv(med_logs_path)
            df = df[df["patient_id"].astype(str) == str(patient_id)]
            if not df.empty:
                total = len(df)
                missed = (df["status"].str.lower() == "missed").sum() if "status" in df.columns else 0
                taken = (df["status"].str.lower() == "taken").sum() if "status" in df.columns else total - missed
        
        # Compute average severity
        avg_sev = sum([t["avg_severity"] or 0 for t in trends]) / len(trends) if trends else 0
        
        # Determine risk
        risk = score_risk(avg_sev, missed)
        
        # Compose summary text
        pname = patient.get("name", f"Patient {patient_id}")
        cg_name = cg.get("name", "(Unknown)")
        cg_rel = cg.get("relationship", "Caregiver")
        
        if not trends:
            sym_text = f"{pname} reported no major symptoms in the last {days} days."
        else:
            parts = []
            for t in trends[:3]:
                parts.append(f"{t['symptom']} {int(t['freq'])}× (avg severity {t['avg_severity']:.1f})")
            sym_text = f"{pname} reported " + ", ".join(parts) + f" in the last {days} days."
        
        med_text = ""
        if missed + taken > 0:
            med_text = f" Out of {missed + taken} doses, {missed} were missed."
        
        overall_text = f"{sym_text}{med_text} Overall status: {risk}."
        
        summary = (
            f"Caregiver Update for {pname} ({cg_rel}: {cg_name})\n"
            f"- {overall_text}\n"
            f"Recommendation: Please check in if risk is MODERATE or HIGH."
        )
        
        return {
            "ts": now_iso(),
            "agent": "CaregiverCommunicationAgent",
            "patient_id": patient_id,
            "patient_name": pname,
            "caregiver_id": cg.get("caregiver_id"),
            "caregiver_name": cg_name,
            "risk_level": risk,
            "symptom_trends": trends,
            "missed_doses": missed,
            "summary_text": summary,
        }
    
    def summarize_weekly_all(self, days: int = 7) -> List[Dict[str, Any]]:
        """Generate summaries for all patients with caregivers and consent on file."""
        caregivers_df = self.db.caregivers
        if caregivers_df.empty:
            return []
        
        results = []
        for _, cg in caregivers_df.iterrows():
            if str(cg.get("consent_on_file", "")).strip().lower() not in ("true", "1", "yes"):
                continue
            
            # Find all patients linked to this caregiver
            pid_list = self.db.patients[
                self.db.patients["primary_caregiver_id"].astype(str) == str(cg["caregiver_id"])
            ]["patient_id"].tolist()
            
            for pid in pid_list:
                rec = self.summarize_one(str(pid), days=days)
                if rec:
                    results.append(rec)
        
        return results


def caregiver_node(state: VoiceAgentState) -> VoiceAgentState:
    """Caregiver agent node"""
    patient_id = state.get("patient_id")
    
    if not patient_id:
        response = "Please provide an 8-digit patient ID to generate a caregiver summary."
        state["caregiver_response"] = response
        state["response"] = response
        # Log entry for error case
        log_entry = {
            "ts": now_iso(),
            "agent": "CaregiverCommunicationAgent",
            "patient_id": None,
            "input": state.get("user_input", ""),
            "response": response,
            "provider": None,
            "model": None,
            "actions": {"action": "error", "reason": "missing_patient_id"},
            "policies": {
                "scope": AGENT_POLICY.get("scope", []),
                "restrictions": AGENT_POLICY.get("restrictions", [])
            }
        }
        state["log_entry"] = log_entry
        return state
    
    service = CaregiverService()
    # Get time window from policy file (actual value used)
    time_window_days = AGENT_POLICY.get("data_aggregation", {}).get("time_window_days", 7)
    record = service.summarize_one(patient_id, days=time_window_days)
    
    if not record:
        response = f"Patient {patient_id} has no linked caregiver with consent on file."
        state["caregiver_response"] = response
        state["response"] = response
        # Extract consent requirement from policy/restrictions
        consent_required = "requires consent on file" in AGENT_POLICY.get("restrictions", [])
        # Log entry for no caregiver case
        log_entry = {
            "ts": now_iso(),
            "agent": "CaregiverCommunicationAgent",
            "patient_id": patient_id,
            "input": state.get("user_input", ""),
            "response": response,
            "provider": None,
            "model": None,
            "actions": {"action": "error", "reason": "no_caregiver_or_consent"},
            "policies": {
                "scope": AGENT_POLICY.get("scope", []),
                "restrictions": AGENT_POLICY.get("restrictions", []),
                "consent_required": consent_required  # From policy restrictions
            }
        }
        state["log_entry"] = log_entry
        return state
    
    response = record["summary_text"]
    state["caregiver_response"] = response
    state["response"] = response
    
    # Extract actions from actual execution (what actually happened)
    # Use the actual time_window_days that was used in the function call
    actions = {
        "patient_id": patient_id,                    # Actual patient processed
        "caregiver_id": record.get("caregiver_id"),  # Actual caregiver ID
        "risk_level": record.get("risk_level"),      # Actual risk calculated
        "days": time_window_days,                    # Actual time window used (from policy)
        "symptom_trends_count": len(record.get("symptom_trends", [])),  # Actual trends found
        "missed_doses": record.get("missed_doses", 0)  # Actual missed doses
    }
    
    # Extract policies that were actually applied/checked
    policies_applied = []
    if record.get("caregiver_id"):  # Consent check was performed
        policies_applied.append("consent_verification")
    
    # Extract consent requirement from policy restrictions (not hardcoded)
    consent_required = "requires consent on file" in AGENT_POLICY.get("restrictions", [])
    
    policies = {
        "policies_applied": policies_applied,  # Only policies that were actually checked
        "scope": AGENT_POLICY.get("scope", []),  # Available scope from policy file
        "consent_required": consent_required,  # From policy restrictions
        "time_window_days": time_window_days  # Actual time window from policy
    }
    
    # Enhance log entry with actions, policies, and provider/model (null for caregiver as it doesn't use LLM)
    log_entry = {
        **record,
        "provider": None,  # Caregiver doesn't use LLM
        "model": None,
        "actions": actions,
        "policies": policies
    }
    state["log_entry"] = log_entry
    
    # Log to file
    # Caregiver logging disabled per user request
    # log_caregiver(record, write_txt=True)
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

