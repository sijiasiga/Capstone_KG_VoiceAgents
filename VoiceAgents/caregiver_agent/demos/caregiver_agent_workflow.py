"""
Caregiver Communication Agent (Summarizer)
- Consumes: symptom logs (from Follow-Up agent), medication logs (from Medication agent),
  patient & caregiver info, appointments (from common_data).
- Produces: weekly caregiver-friendly summary + structured JSON.
- CLI supports: per-patient summary, weekly sweep for all patients with caregiver consent,
  optional TTS voice readout, and simple STT via audio file (if you want to dictate a note).

Run from project root 'VoiceAgents':
  python -m caregiver_agent.demos.caregiver_agent_workflow
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import Counter

# -------------- Import shared DB layer ----------------
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_ROOT not in sys.path:
    sys.path.append(PKG_ROOT)

from common_data.database import DatabaseService  # unified database access

# -------------- Optional TTS --------------------------
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# -------------- Optional STT (not required) ----------
USE_STT = True
try:
    import speech_recognition as sr
except Exception:
    sr = None
    USE_STT = False

# -------------- Output directories -------------------
OUT_DIR = os.path.join(HERE, "logs")
os.makedirs(OUT_DIR, exist_ok=True)
SUMMARY_JSONL = os.path.join(OUT_DIR, "caregiver_summaries.jsonl")
SUMMARY_TXT = os.path.join(OUT_DIR, "caregiver_summaries.txt")

# ------------------------------------------------------
# Utilities
# ------------------------------------------------------
def say(text: str, voice: bool = False):
    print(f"\nAgent: {text}")
    if voice and pyttsx3 is not None:
        try:
            eng = pyttsx3.init()
            eng.setProperty("rate", 155)
            eng.say(text)
            eng.runAndWait()
        except Exception:
            pass

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def save_jsonline(path: str, obj: Dict[str, Any]):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def append_text(path: str, text: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")

# ------------------------------------------------------
# Risk scoring helpers
# ------------------------------------------------------
def score_risk(avg_sev: float, missed: int) -> str:
    """Simple heuristic for overall patient risk."""
    if avg_sev >= 7 or missed >= 3:
        return "HIGH"
    if avg_sev >= 4 or missed >= 1:
        return "MODERATE"
    return "LOW"

# ------------------------------------------------------
# Caregiver Agent
# ------------------------------------------------------
class CaregiverAgent:
    def __init__(self, voice: bool = False):
        self.voice = voice
        self.db = DatabaseService()

    def summarize_one(self, patient_id: str, days: int = 7) -> Optional[Dict[str, Any]]:
        patient = self.db.get_patient(patient_id)
        if not patient:
            say(f"No patient found for ID {patient_id}.", self.voice)
            return None

        cg_id = patient.get("primary_caregiver_id")
        caregivers_df = self.db.caregivers
        if caregivers_df.empty or str(cg_id) not in caregivers_df["caregiver_id"].astype(str).values:
            say(f"Patient {patient.get('name','')} has no linked caregiver.", self.voice)
            return None

        cg = caregivers_df[caregivers_df["caregiver_id"].astype(str) == str(cg_id)].iloc[0].to_dict()
        if str(cg.get("consent_on_file", "")).strip().lower() not in ("true", "1", "yes"):
            say(f"Caregiver consent not on file for patient {patient.get('name','')}.", self.voice)
            return None

        # ---------------- Data aggregation ----------------
        trends = self.db.get_symptom_trends(patient_id, days)
        meds = self.db.get_prescriptions(patient_id)

        # Medication adherence summary (if med_logs.csv exists)
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

        # ---------------- Compose summary text ----------------
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
            f"• {overall_text}\n"
            f"Recommendation: Please check in if risk is MODERATE or HIGH."
        )

        # ---------------- Output records ----------------
        record = {
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

        save_jsonline(SUMMARY_JSONL, record)
        append_text(SUMMARY_TXT, summary + "\n")
        say(summary, self.voice)
        return record

    def summarize_weekly_all(self, days: int = 7) -> List[Dict[str, Any]]:
        caregivers_df = self.db.caregivers
        if caregivers_df.empty:
            say("No caregivers found.", self.voice)
            return []
        results = []
        for _, cg in caregivers_df.iterrows():
            if str(cg.get("consent_on_file", "")).strip().lower() not in ("true", "1", "yes"):
                continue
            pid_list = self.db.patients[self.db.patients["primary_caregiver_id"] == cg["caregiver_id"]]["patient_id"].tolist()
            for pid in pid_list:
                rec = self.summarize_one(str(pid), days=days)
                if rec:
                    results.append(rec)
        say(f"Generated {len(results)} caregiver summaries.", self.voice)
        return results


# ------------------------------------------------------
# CLI
# ------------------------------------------------------
def stt_transcribe(path: str) -> str:
    if not USE_STT or sr is None or not os.path.exists(path):
        return ""
    try:
        r = sr.Recognizer()
        with sr.AudioFile(path) as source:
            audio = r.record(source)
        try:
            return r.recognize_sphinx(audio)
        except Exception:
            return r.recognize_google(audio)
    except Exception:
        return ""

def main():
    print("Caregiver Communication Agent (Summarizer + TTS/STT optional)")
    print("Commands:")
    print("  :voice on | :voice off     -> toggle TTS")
    print("  pid <8digit>               -> set patient_id context (default 10001217)")
    print("  one                        -> summarize current patient (last 7 days)")
    print("  weekly                     -> summarize all eligible patients (last 7 days)")
    print("  :stt <path.wav>            -> transcribe note (demo only)")
    print("  quit                       -> exit")

    agent = CaregiverAgent(voice=False)
    patient_id = "10001217"

    while True:
        user = input("\nCommand: ").strip()
        low = user.lower()
        if low == "quit":
            break
        elif low.startswith(":voice "):
            arg = low.split(" ", 1)[1].strip()
            agent.voice = (arg == "on")
            print(f"[voice] {'Enabled' if agent.voice else 'Disabled'}")
        elif low.startswith("pid "):
            patient_id = user.split(" ", 1)[1].strip()
            print(f"[context] patient_id set to {patient_id}")
        elif low == "one":
            agent.summarize_one(patient_id, days=7)
        elif low == "weekly":
            agent.summarize_weekly_all(days=7)
        elif low.startswith(":stt "):
            path = user.split(" ", 1)[1].strip().strip('"')
            text = stt_transcribe(path)
            print(f"[stt] → {text or '(no transcription)'}")
        else:
            print("Unknown command. Try: one | weekly | pid <id> | :voice on/off | :stt <file> | quit")

if __name__ == "__main__":
    main()
