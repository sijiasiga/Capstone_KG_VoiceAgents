"""
Medication Education Agent (LLM + Rules + Templates + Optional STT/TTS)
English-only version
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional
from common_data.database import DatabaseService

# ---------- Optional voice output ----------
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# ---------- Optional speech-to-text ----------
USE_STT = True
try:
    import speech_recognition as sr
except Exception:
    sr = None
    USE_STT = False

# ---------- Optional LLM ----------
USE_LLM = True
try:
    from openai import OpenAI
    client = OpenAI()  # requires OPENAI_API_KEY
except Exception:
    USE_LLM = False
    client = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "..", "drug_knowledge.csv")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


# ---------------------------------------------------
# Utility Functions
# ---------------------------------------------------
def say(text: str, use_voice: bool = False):
    print(f"\nAgent: {text}")
    if use_voice and pyttsx3 is not None:
        try:
            engine = pyttsx3.init()

            # Force English voice (US or UK)
            voices = engine.getProperty('voices')
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
                engine.setProperty('voice', english_voice)

            engine.setProperty("rate", 155)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass


def stt_transcribe(audio_path: str) -> str:
    """Transcribe an audio file (wav/mp3) to text."""
    if not USE_STT or not os.path.exists(audio_path):
        return ""

    ext = os.path.splitext(audio_path)[-1].lower()
    if ext in [".wav", ".flac", ".aif", ".aiff"]:
        try:
            r = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = r.record(source)
            try:
                return r.recognize_sphinx(audio)
            except Exception:
                return r.recognize_google(audio)
        except Exception:
            return ""

    if USE_LLM and client is not None:
        try:
            with open(audio_path, "rb") as f:
                tr = client.audio.transcriptions.create(model="gpt-4o-transcribe", file=f)
            return tr.text.strip()
        except Exception:
            return ""
    return ""


def mic_listen_once(timeout: int = 5, phrase_time_limit: int = 10) -> str:
    """Capture one utterance from the microphone."""
    if not USE_STT or sr is None:
        return ""
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("[Listening...] Speak now")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            try:
                return r.recognize_sphinx(audio)
            except Exception:
                return r.recognize_google(audio)
        except Exception:
            return ""
    except Exception:
        return ""


def now_iso() -> str:
    import datetime as dt
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def save_jsonline(path: str, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------------------------------------------------
# LLM Helpers
# ---------------------------------------------------
def llm_parse_query(user_text: str) -> Dict:
    """Use LLM to extract intent, drugs, and symptoms."""
    if not USE_LLM or client is None:
        # Fallback simple rules
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
        resp = client.chat.completions.create(model="gpt-4o-mini", temperature=0, messages=[sys, user])
        content = resp.choices[0].message.content.strip()
        return json.loads(content)
    except Exception:
        return {"intent": "general", "language": "en"}


def llm_score_risk(parsed: Dict) -> str:
    """Return RED / ORANGE / GREEN risk."""
    if not USE_LLM or client is None:
        intent = parsed.get("intent")
        if intent == "double_dose":
            return "RED"
        if intent in ["interaction_check", "missed_dose"]:
            return "ORANGE"
        return "GREEN"
    sys = {"role": "system", "content": "Return ONLY a single word: RED, ORANGE, or GREEN."}
    user = {"role": "user", "content": json.dumps(parsed, ensure_ascii=False)}
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", temperature=0, messages=[sys, user])
        return resp.choices[0].message.content.strip().upper()
    except Exception:
        return "GREEN"


# ---------------------------------------------------
# Medication Agent
# ---------------------------------------------------
class MedicationAgent:
    def __init__(self, use_voice: bool = False):
        self.use_voice = use_voice
        self.db = DatabaseService()
        self.drug_knowledge = self._load_drug_knowledge()

    def _load_drug_knowledge(self) -> pd.DataFrame:
        if not os.path.exists(KNOWLEDGE_PATH):
            print(f"[WARN] Missing drug_knowledge.csv at {KNOWLEDGE_PATH}")
            return pd.DataFrame()
        return pd.read_csv(KNOWLEDGE_PATH)

    def _get_drug_info(self, name: str) -> Optional[dict]:
        df = self.drug_knowledge
        match = df[df["drug_name"].str.lower() == name.lower()]
        return match.iloc[0].to_dict() if not match.empty else None

    def handle(self, patient_id: str, user_text: str):
        patient = self.db.get_patient(patient_id)
        if not patient:
            say("Patient not found.", self.use_voice)
            return "Patient not found."

        parsed = llm_parse_query(user_text)
        intent = parsed.get("intent", "general")

        prescriptions = self.db.get_prescriptions(patient_id)
        if not prescriptions:
            say("No prescriptions found for this patient.", self.use_voice)
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

        # Add helpful context for interaction checks
        if intent == "interaction_check" and len(responses) > 1:
            responses.insert(0, "You're taking multiple medications. Here are the interaction warnings:")

        if not responses:
            responses.append("I could not interpret your medication question clearly.")

        combined = " ".join(responses)
        # Risk-level prefix (no emojis for Windows compatibility)
        if risk == "RED":
            combined = "[HIGH RISK] Please seek immediate medical care. " + combined
        elif risk == "ORANGE":
            combined = "[ALERT] Please contact your clinician soon. " + combined

        say(combined, self.use_voice)

        # Log interaction
        log = {
            "ts": now_iso(),
            "agent": "MedicationEducationAgent",
            "patient_id": patient_id,
            "input": user_text,
            "intent": intent,
            "risk_level": risk,
            "response": combined,
        }
        save_jsonline(os.path.join(LOG_DIR, "med_agent_log.jsonl"), log)

        return combined


# ---------------------------------------------------
# Command Line Interface
# ---------------------------------------------------
def main():
    print("Medication Education Agent (LLM + Rules + STT/TTS)")
    print("Commands:")
    print("  :voice on | :voice off        -> toggle text-to-speech")
    print("  :stt <path_to_audio.wav/mp3>  -> transcribe then process")
    print("  :mic on                       -> record one sentence")
    print("  pid <8digit>                  -> switch patient_id (default: 10004235)")
    print("  quit                          -> exit")

    agent = MedicationAgent(use_voice=False)
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
            agent.use_voice = arg == "on"
            print(f"[voice] {'Enabled' if agent.use_voice else 'Disabled'}")
        elif low.startswith(":stt "):
            path = user.split(" ", 1)[1].strip().strip('"')
            if not os.path.exists(path):
                print(f"[stt] file not found: {path}")
                continue
            text = stt_transcribe(path)
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
