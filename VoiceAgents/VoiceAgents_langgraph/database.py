"""
Database Service for LangGraph VoiceAgents
Uses local data folder instead of common_data
"""
import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# -------------------------------------------------------------------
# Local data directory setup
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

SYMPTOMS_LOG_CSV = os.path.join(LOG_DIR, "symptom_logs.csv")
APPOINTMENTS_CSV = os.path.join(DATA_DIR, "appointments.csv")

# Ensure the symptom log exists
if not os.path.exists(SYMPTOMS_LOG_CSV):
    with open(SYMPTOMS_LOG_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ts_iso", "patient_id", "symptom", "severity", "note"])
        w.writeheader()


# -------------------------------------------------------------------
# Unified Database Service
# -------------------------------------------------------------------
class DatabaseService:
    """
    Unified data access layer for LangGraph Voice Agents.
    Uses local data folder in VoiceAgents_langgraph/data/
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.patients = self._load_csv("patients.csv")
        self.appointments = self._load_csv("appointments.csv")
        self.prescriptions = self._load_csv("prescriptions.csv")
        self.caregivers = self._load_csv("caregivers.csv")
        self.policy = self._load_json("policy_config.json")

    # ------------------ Loaders ------------------
    def _load_csv(self, filename):
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"[WARN] Missing file: {filename}")
            return pd.DataFrame()
        return pd.read_csv(path)

    def _load_json(self, filename):
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"[WARN] Missing file: {filename}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------ Core Queries ------------------
    def get_patient(self, patient_id: str):
        df = self.patients[self.patients["patient_id"].astype(str) == str(patient_id)]
        return df.iloc[0].to_dict() if not df.empty else None

    def get_appointments(self, patient_id: str):
        df = self.appointments[self.appointments["patient_id"].astype(str) == str(patient_id)]
        return df.to_dict(orient="records")

    def get_prescriptions(self, patient_id: str):
        df = self.prescriptions[self.prescriptions["patient_id"].astype(str) == str(patient_id)]
        return df.to_dict(orient="records")

    def get_caregiver(self, caregiver_id: str):
        df = self.caregivers[self.caregivers["caregiver_id"].astype(str) == str(caregiver_id)]
        return df.iloc[0].to_dict() if not df.empty else None

    def get_policy_rules(self):
        return self.policy

    # ------------------ Appointment Helper ------------------
    def get_next_appointment(self, patient_id: str) -> Optional[Dict]:
        """Return the soonest upcoming appointment for a patient."""
        if not os.path.exists(APPOINTMENTS_CSV):
            return None
        rows = []
        with open(APPOINTMENTS_CSV, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                if str(row.get("patient_id")) == str(patient_id):
                    rows.append(row)
        # pick the nearest future date
        future = []
        now = datetime.utcnow()
        for row in rows:
            try:
                dt = datetime.fromisoformat(row["appointment_date"])
            except Exception:
                try:
                    dt = datetime.strptime(row["appointment_date"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
            if dt >= now:
                row["_dt"] = dt
                future.append(row)
        if not future:
            return None
        future.sort(key=lambda x: x["_dt"])
        best = future[0]
        best.pop("_dt", None)
        return best

    # ------------------ Symptom Logs ------------------
    def upsert_symptom_log(self, patient_id: str, symptom: str, severity: int, note: str = "") -> None:
        """Append one symptom record to CSV."""
        ts_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        with open(SYMPTOMS_LOG_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ts_iso", "patient_id", "symptom", "severity", "note"])
            w.writerow({
                "ts_iso": ts_iso,
                "patient_id": patient_id,
                "symptom": symptom,
                "severity": severity,
                "note": note
            })

    def add_symptom_log(self, patient_id, symptoms, severity=None):
        """Add multiple symptoms at once (used by Follow-Up Agent)."""
        path = SYMPTOMS_LOG_CSV
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            for s in symptoms:
                writer.writerow([now, patient_id, s, severity or "", ""])

    def get_recent_symptoms(self, patient_id, days=7) -> List[Dict]:
        """Return all symptom logs for this patient within the past N days."""
        path = SYMPTOMS_LOG_CSV
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path)
        if "ts_iso" not in df.columns:
            return []
        df["date"] = pd.to_datetime(df["ts_iso"].str.rstrip("Z"))
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = df[(df["patient_id"].astype(str) == str(patient_id)) & (df["date"] >= cutoff)]
        return recent.to_dict("records")

    def get_symptom_logs_window(self, patient_id: str, symptom: str, days: int = 7) -> List[Dict]:
        """Return symptom logs for a specific symptom over the past `days`."""
        if not os.path.exists(SYMPTOMS_LOG_CSV):
            return []
        out = []
        cutoff = datetime.utcnow() - timedelta(days=days)
        with open(SYMPTOMS_LOG_CSV, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                if str(row["patient_id"]) != str(patient_id):
                    continue
                if row["symptom"].lower() != symptom.lower():
                    continue
                try:
                    ts = datetime.fromisoformat(row["ts_iso"].rstrip("Z"))
                except Exception:
                    continue
                if ts >= cutoff:
                    out.append({
                        "ts_iso": row["ts_iso"],
                        "severity": int(row["severity"]) if row["severity"] else None,
                        "note": row.get("note", "")
                    })
        return out

    # ------------------ Trend Summary ------------------
    def get_symptom_trends(self, patient_id: str, days: int = 7) -> List[Dict]:
        """
        Return trend summary: symptom, frequency, average severity (for caregiver reports).
        """
        logs = self.get_recent_symptoms(patient_id, days=days)
        if not logs:
            return []
        df = pd.DataFrame(logs)
        if df.empty or "symptom" not in df.columns:
            return []
        grouped = (
            df.groupby("symptom", as_index=False)
            .agg(freq=("symptom", "count"), avg_severity=("severity", "mean"))
            .sort_values("freq", ascending=False)
        )
        return grouped.to_dict("records")

