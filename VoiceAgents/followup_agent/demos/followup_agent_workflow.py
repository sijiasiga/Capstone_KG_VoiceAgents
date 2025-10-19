"""
Follow-Up & Monitoring Agent (LLM + Rules + Optional STT/TTS)
- Input: symptom phrase or voice, optional severity (0-10)
- Processing: map to SNOMED, count occurrences in last 7 days, apply rules
- Output: reassurance/escalation + structured log
"""

import os
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Path gymnastics so imports work no matter where you run from
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
import sys
if PKG_ROOT not in sys.path:
    sys.path.append(PKG_ROOT)

from common_data.database import DatabaseService  # shared DB

# -------- Optional TTS ----------
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# -------- Optional STT ----------
USE_STT = True
try:
    import speech_recognition as sr
except Exception:
    sr = None
    USE_STT = False

# -------- Optional LLM ----------
USE_LLM = True
try:
    from openai import OpenAI
    client = OpenAI()
except Exception:
    client = None
    USE_LLM = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CODEBOOK_CSV = os.path.join(BASE_DIR, "..", "symptom_codes.csv")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def say(text: str, voice: bool = False):
    print(f"\nAgent: {text}")
    if voice and pyttsx3 is not None:
        try:
            eng = pyttsx3.init()

            # Force English voice (US or UK)
            voices = eng.getProperty('voices')
            english_voice = None
            for v in voices:
                # Look for English voices (US or UK)
                if 'english' in v.name.lower() or 'en_' in v.id.lower() or 'en-' in v.id.lower():
                    english_voice = v.id
                    break
                # Fallback: look for common English voice names on Windows
                if 'david' in v.name.lower() or 'zira' in v.name.lower() or 'mark' in v.name.lower():
                    english_voice = v.id
                    break

            if english_voice:
                eng.setProperty('voice', english_voice)

            eng.setProperty("rate", 155)
            eng.say(text)
            eng.runAndWait()
        except Exception:
            pass

def stt_transcribe(path: str) -> str:
    if not USE_STT or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[-1].lower()
    # Prefer offline recognizer for wav, else Google
    if ext in [".wav",".aif",".aiff",".flac"]:
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
    # If LLM audio model available
    if USE_LLM and client is not None:
        try:
            with open(path, "rb") as f:
                tr = client.audio.transcriptions.create(model="gpt-4o-transcribe", file=f)
            return tr.text.strip()
        except Exception:
            return ""
    return ""

def mic_listen_once(timeout=5, phrase_time_limit=10) -> str:
    if not USE_STT or sr is None:
        return ""
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("[LISTENING...] Speak now")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            return r.recognize_sphinx(audio)
        except Exception:
            return r.recognize_google(audio)
    except Exception:
        return ""

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def save_jsonline(path: str, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ---------------- Symptom Mapping -----------------

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
    # LLM fallback: try to map quickly
    if USE_LLM and client is not None:
        sysmsg = {"role":"system","content":"Return ONLY valid JSON with fields: canonical, snomed"}
        usr = {"role":"user","content": f"Map this symptom phrase to a canonical term and SNOMED code if possible, else guess canonical='other' and snomed='NA'. Phrase: {text}"}
        try:
            resp = client.chat.completions.create(model="gpt-4o-mini", temperature=0, messages=[sysmsg, usr])
            j = json.loads(resp.choices[0].message.content.strip())
            if isinstance(j, dict) and j.get("canonical"):
                return {"canonical": j.get("canonical","other"), "snomed": j.get("snomed","NA")}
        except Exception:
            pass
    return {"canonical": "other", "snomed": "NA"}

def llm_parse_symptom(user_text: str) -> Dict:
    """Extract symptom phrase + severity_0_10."""
    if not USE_LLM or client is None:
        # Simple heuristic fallback
        sev = 0
        for k in range(10, -1, -1):
            if f"{k}/10" in user_text or f"{k} out of 10" in user_text:
                sev = k; break
        return {"symptom_text": user_text, "severity_0_10": sev}
    sysm = {"role":"system","content":"Return ONLY valid JSON with fields: symptom_text, severity_0_10 (0-10 or null)."}
    usr = {"role":"user","content": f"Extract symptom and optional numeric severity from: {user_text}"}
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", temperature=0, messages=[sysm, usr])
        return json.loads(resp.choices[0].message.content.strip())
    except Exception:
        return {"symptom_text": user_text, "severity_0_10": None}

# --------------- Business Rules -------------------
# From assignment:
# - Map to SNOMED
# - Alert if severe OR repeats ≥2 times in a week
RED_SEVERITY = 8   # threshold for "severe"
REPEAT_WINDOW_DAYS = 7
REPEAT_THRESHOLD = 2

def evaluate_alert(db: DatabaseService, patient_id: str, canonical_symptom: str, severity: Optional[int]) -> Dict:
    logs = db.get_symptom_logs_window(patient_id, canonical_symptom, days=REPEAT_WINDOW_DAYS)
    count_recent = len(logs)
    is_repeat = count_recent >= REPEAT_THRESHOLD - 1  # current event makes it ≥2
    is_severe = (severity is not None and severity >= RED_SEVERITY)
    alert = bool(is_severe or is_repeat)
    tier = "RED" if is_severe else ("ORANGE" if is_repeat else "GREEN")
    return {"alert": alert, "tier": tier, "recent_count": count_recent}

# --------------- Agent ----------------------------

class FollowUpAgent:
    def __init__(self, voice: bool = False):
        self.voice = voice
        self.db = DatabaseService()

    def handle(self, patient_id: str, text: str) -> str:
        """
        Main entry point for symptom follow-up.
        Logs the reported symptoms and returns a clear, patient-friendly summary.
        """
        from common_data.database import DatabaseService
        import re, json

        db = DatabaseService()
        text_lower = text.lower()

        # --- Basic pattern extraction (extendable) ---
        symptoms = []
        severity = None

        # extract severity (like "7 out of 10" or "pain 6")
        m = re.search(r'(\d+)\s*(?:out\s*of\s*10|/10)?', text_lower)
        if m:
            try:
                val = int(m.group(1))
                if 0 <= val <= 10:
                    severity = val
            except Exception:
                pass

        for kw in ["pain", "fever", "dizzy", "dizziness",
                "shortness of breath", "breathless", "cough", "fatigue"]:
            if kw in text_lower:
                symptoms.append(kw)

        if not symptoms:
            msg = "I didn't detect any specific symptoms. Could you describe what you're feeling?"
            print(f"\nAgent: {msg}")
            return msg

        # --- Log symptom(s) into the shared DB CSV ---
        db.add_symptom_log(patient_id, symptoms, severity)

        # --- Retrieve recent history for context ---
        recent = db.get_recent_symptoms(patient_id, days=7)
        unique_symptoms = list({s["symptom"] for s in recent})

        # --- Construct response ---
        symptom_str = ", ".join(symptoms)
        response = f"I’ve recorded your symptom {symptom_str}"
        if severity is not None:
            response += f" (severity {severity}/10)"
        response += "."

        if len(unique_symptoms) > 1:
            response += f" You also mentioned {', '.join(unique_symptoms[:-1])} earlier this week."

        if severity and severity >= 7:
            response += " Since the severity is high, I’ll notify your provider."
        else:
            response += " I’ll keep this logged for your next review."

        print(f"\nAgent: {response}")
        return response


# ---------------- CLI -----------------------------

def main():
    print("Follow-Up & Monitoring Agent (LLM + Rules + STT/TTS)")
    print("Commands:")
    print("  :voice on | :voice off        -> toggle TTS")
    print("  :stt <path_to_audio.wav/mp3>  -> transcribe then process")
    print("  :mic on                       -> capture one utterance")
    print("  pid <8digit>                  -> set patient_id (default 10004235)")
    print("  quit                          -> exit")

    agent = FollowUpAgent(voice=False)
    patient_id = "10004235"

    while True:
        user = input("\nPatient (or command): ").strip()
        low = user.lower()

        if low == "quit":
            break
        elif low.startswith("pid "):
            patient_id = user.split(" ", 1)[1].strip()
            print(f"[context] patient_id set to {patient_id}")
        elif low.startswith(":voice "):
            arg = low.split(" ", 1)[1].strip()
            agent.voice = (arg == "on")
            print(f"[voice] {'Enabled' if agent.voice else 'Disabled'}")
        elif low.startswith(":stt "):
            path = user.split(" ", 1)[1].strip().strip('"')
            if not os.path.exists(path):
                print(f"[stt] file not found: {path}")
                continue
            text = stt_transcribe(path)
            if not text:
                print("[stt] transcription failed.")
                continue
            print(f"[stt] → {text}")
            agent.handle(patient_id, text)
        elif low == ":mic on":
            text = mic_listen_once()
            if not text:
                print("[mic] no speech detected.")
                continue
            print(f"[mic→stt] {text}")
            agent.handle(patient_id, text)
        else:
            agent.handle(patient_id, user)

if __name__ == "__main__":
    main()
