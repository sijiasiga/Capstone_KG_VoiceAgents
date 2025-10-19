"""
Orchestration Agent (Router + STT/TTS + Logging)

Purpose:
---------
- Listen to user input (text, mic, or audio file)
- Detect which agent should handle it:
  appointment | followup | medication | caregiver | help
- Route to the appropriate specialized agent
- Log all events in JSONL for traceability

Usage:
-------
From project root 'VoiceAgents':
    python -m orchestration_agent.demos.orchestration_agent_workflow
"""

import os
import sys
import json
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# ----------------- Path setup -----------------
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_ROOT not in sys.path:
    sys.path.append(PKG_ROOT)

# ----------------- Optional TTS -----------------
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# ----------------- Optional STT -----------------
USE_STT = True
try:
    import speech_recognition as sr
except Exception:
    sr = None
    USE_STT = False

# ----------------- Optional LLM -----------------
USE_LLM = True
try:
    from openai import OpenAI
    client = OpenAI()
except Exception:
    client = None
    USE_LLM = False


# ----------------- Import Adapters -----------------

# Appointment Agent
AppointmentAdapter = None
try:
    from appointment_agent.demos.appointment_agent_workflow import AppointmentDemo
    class _AppointmentAdapter:
        def __init__(self, voice: bool = False):
            self.app = AppointmentDemo(use_voice=voice)
        def handle(self, text: str) -> str:
            result = self.app.run_turn(text)
            return result.get("response", "(no response)")
    AppointmentAdapter = _AppointmentAdapter
except Exception:
    pass


# Follow-Up Agent
FollowUpAdapter = None
try:
    from followup_agent.demos.followup_agent_workflow import FollowUpAgent
    class _FollowUpAdapter:
        def __init__(self, voice: bool = False):
            self.app = FollowUpAgent(voice=voice)
        def handle(self, patient_id: str, text: str) -> str:
            return self.app.handle(patient_id, text)
    FollowUpAdapter = _FollowUpAdapter
except Exception:
    pass


# Medication Agent
MedicationAdapter = None
try:
    from medication_agent.demos.medication_agent_workflow import MedicationAgent
    class _MedicationAdapter:
        def __init__(self, voice: bool = False):
            self.app = MedicationAgent()
        def handle(self, patient_id: str, text: str) -> str:
            return self.app.handle(patient_id, text)
    MedicationAdapter = _MedicationAdapter
except Exception:
    class _MedicationAdapterStub:
        def __init__(self, voice: bool = False):
            self.voice = voice
        def handle(self, patient_id: str, text: str) -> str:
            return "[Medication] Adapter not found. Please run the medication agent module or adjust import."
    MedicationAdapter = _MedicationAdapterStub


# Caregiver Agent
CaregiverAdapter = None
try:
    from caregiver_agent.demos.caregiver_agent_workflow import CaregiverAgent
    class _CaregiverAdapter:
        def __init__(self, voice: bool = False):
            self.app = CaregiverAgent(voice=voice)
        def handle(self, patient_id: str) -> str:
            rec = self.app.summarize_one(patient_id, days=7)
            return rec["summary_text"] if rec else "[Caregiver] No summary generated."
    CaregiverAdapter = _CaregiverAdapter
except Exception:
    class _CaregiverAdapterStub:
        def __init__(self, voice: bool = False):
            self.voice = voice
        def handle(self, patient_id: str) -> str:
            return "[Caregiver] Adapter not found. Please run the caregiver agent module or adjust import."
    CaregiverAdapter = _CaregiverAdapterStub


# ----------------- Logging -----------------
LOG_DIR = os.path.join(HERE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
ORCH_LOG = os.path.join(LOG_DIR, "orchestration_log.jsonl")

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def log_event(obj: Dict[str, Any]) -> None:
    with open(ORCH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ----------------- Helpers -----------------
def _speak_in_background(text: str):
    """Helper function to run TTS in background thread."""
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


def say(text: str, voice: bool = False):
    """Print text immediately and optionally speak it in background thread."""
    print(f"\nAgent: {text}")
    if voice and pyttsx3 is not None:
        # Run TTS in background thread so it doesn't block UI updates
        tts_thread = threading.Thread(target=_speak_in_background, args=(text,), daemon=True)
        tts_thread.start()


def stt_transcribe(path: str) -> str:
    if not USE_STT or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[-1].lower()
    if sr is not None and ext in [".wav", ".aif", ".aiff", ".flac"]:
        try:
            r = sr.Recognizer()
            with sr.AudioFile(path) as source:
                audio = r.record(source)
            return r.recognize_google(audio)
        except Exception:
            return ""
    return ""


def mic_listen_once(timeout=5, phrase_time_limit=10) -> str:
    """
    Listen to microphone once and transcribe.
    Returns transcribed text or empty string on failure.
    """
    if not USE_STT or sr is None:
        return ""
    try:
        r = sr.Recognizer()
        # Improved settings for better accuracy
        r.energy_threshold = 200  # More sensitive (lower value)
        r.dynamic_energy_threshold = True
        r.dynamic_energy_adjustment_damping = 0.15
        r.dynamic_energy_ratio = 1.5
        r.pause_threshold = 1.0  # Wait longer before considering phrase complete
        r.phrase_threshold = 0.3  # Minimum seconds of speaking audio before considering phrase
        r.non_speaking_duration = 0.5  # Seconds of non-speaking audio to keep on both sides

        with sr.Microphone(sample_rate=16000) as source:
            print("[Listening...] Speak now")
            # Longer calibration for better noise cancellation
            r.adjust_for_ambient_noise(source, duration=1.5)
            # Listen for audio
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

        print("[Processing...] Transcribing audio")
        # Try Google Speech Recognition with show_all to get alternatives
        try:
            # First try: standard recognition
            text = r.recognize_google(audio, language='en-US', show_all=False)
            return text
        except:
            # Fallback: try without language specification
            text = r.recognize_google(audio)
            return text
    except sr.WaitTimeoutError:
        print("[Error] No speech detected within timeout")
        return ""
    except sr.UnknownValueError:
        print("[Error] Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"[Error] API error: {e}")
        return ""
    except Exception as e:
        print(f"[Error] Unexpected error: {e}")
        return ""


# ----------------- Intent Parsing -----------------
INTENT_LABELS = ["appointment", "followup", "medication", "caregiver", "help"]

def parse_intent_llm(text: str) -> Dict[str, Any]:
    """
    Use OpenAI LLM to classify the user's intent.
    """
    if not USE_LLM or client is None:
        return parse_intent_rules(text)

    SYSTEM_PROMPT = """
    You are a routing assistant for a healthcare voice triage system.
    Classify this patient message into one of:
    appointment | followup | medication | caregiver | help
    Extract any 8-digit patient ID if present.
    Reply only in JSON like:
    {"intent": "followup", "patient_id": "10004235"}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": text}
            ]
        )
        raw = resp.choices[0].message.content.strip()
        out = json.loads(raw)
        intent = (out.get("intent") or "help").lower()
        if intent not in INTENT_LABELS:
            intent = "help"

        pid = out.get("patient_id")

        # ⚙️ fallback safeguard
        if intent == "help":
            rule_fallback = parse_intent_rules(text)
            print(f"[DEBUG] LLM fallback → using rule intent {rule_fallback['intent']}")
            return rule_fallback

        print(f"[DEBUG] LLM intent → {intent}, patient_id → {pid}")
        return {"intent": intent, "patient_id": pid}

    except Exception:
        return parse_intent_rules(text)


def parse_intent_rules(text: str) -> Dict[str, Any]:
    t = text.lower()
    intent = "help"

    if any(k in t for k in ["appointment", "reschedule", "schedule", "cancel", "doctor", "visit", "check my appointment"]):
        intent = "appointment"
    elif any(k in t for k in [
        "breathless", "shortness of breath", "symptom", "dizzy", "dizziness",
        "pain", "fever", "feel", "tired", "fatigue", "weakness", "chest pain"
    ]):
        intent = "followup"
    elif any(k in t for k in ["med", "medication", "pill", "dose", "side effect", "missed dose", "take with food"]):
        intent = "medication"
    elif any(k in t for k in ["caregiver", "weekly summary", "check on them", "update for parent", "mother", "father"]):
        intent = "caregiver"

    pid = None
    import re
    m = re.search(r"\b(\d{8})\b", text)
    if m:
        pid = m.group(1)

    print(f"[DEBUG] Rule intent → {intent}, patient_id → {pid}")
    return {"intent": intent, "patient_id": pid}


# ----------------- Orchestrator -----------------
class Orchestrator:
    def __init__(self, voice: bool = False):
        self.voice = voice
        self.patient_id = "10004235"
        # Disable voice in sub-agents - orchestrator will handle TTS
        self.appointment = AppointmentAdapter(voice=False) if AppointmentAdapter else None
        self.followup = FollowUpAdapter(voice=False) if FollowUpAdapter else None
        self.medication = MedicationAdapter(voice=False) if MedicationAdapter else None
        self.caregiver = CaregiverAdapter(voice=False) if CaregiverAdapter else None

    def route(self, user_text: str) -> str:
        parsed = parse_intent_llm(user_text)
        intent = parsed.get("intent", "help")
        pid = parsed.get("patient_id") or self.patient_id

        decision = {
            "ts": now_iso(),
            "agent": "OrchestrationAgent",
            "input": user_text,
            "intent": intent,
            "patient_id": pid
        }

        reply = ""
        if intent == "appointment" and self.appointment:
            # Prepend patient ID if not already in text
            if pid and pid not in user_text:
                enhanced_text = f"I am patient {pid}, {user_text}"
            else:
                enhanced_text = user_text
            reply = self.appointment.handle(enhanced_text)
        elif intent == "followup" and self.followup:
            reply = self.followup.handle(pid, user_text)
        elif intent == "medication" and self.medication:
            reply = self.medication.handle(pid, user_text)
        elif intent == "caregiver" and self.caregiver:
            reply = self.caregiver.handle(pid)
        else:
            reply = (
                "I can help with appointments, symptoms (follow-up), medications, and caregiver summaries.\n"
                "Try something like:\n"
                "- 'I am patient 10004235, check my appointment'\n"
                "- 'I feel dizzy 7/10'\n"
                "- 'What are the side effects of metformin?'\n"
                "- 'Give me this week's caregiver update for 10001217'"
            )

        decision["routed_reply"] = reply
        log_event(decision)
        say(reply, self.voice)
        return reply


# ----------------- CLI -----------------
def main():
    print("Orchestration Agent (Router + STT/TTS)")
    print("Commands:")
    print("  :voice on | :voice off            -> toggle TTS")
    print("  pid <8digit>                      -> set default patient_id context")
    print("  :stt <path_to_audio.wav/mp3>      -> transcribe then route")
    print("  :mic on                           -> speak one sentence to route")
    print("  quit                              -> exit")

    orch = Orchestrator(voice=False)

    while True:
        user = input("\nYou (or command): ").strip()
        low = user.lower()

        if low == "quit":
            break
        elif low.startswith(":voice "):
            arg = low.split(" ", 1)[1].strip()
            orch.voice = (arg == "on")
            print(f"[voice] {'Enabled' if orch.voice else 'Disabled'}")
        elif low.startswith("pid "):
            orch.patient_id = user.split(" ", 1)[1].strip()
            print(f"[context] patient_id set to {orch.patient_id}")
        elif low.startswith(":stt "):
            path = user.split(" ", 1)[1].strip().strip('"')
            if not os.path.exists(path):
                print(f"[stt] file not found: {path}")
                continue
            print(f"[stt] transcribing: {path} ...")
            text = stt_transcribe(path)
            print(f"[stt] → {text}")
            orch.route(text)
        elif low == ":mic on":
            text = mic_listen_once()
            if not text:
                print("[mic] no speech detected.")
                continue
            print(f"[mic→stt] {text}")
            orch.route(text)
        else:
            orch.route(user)


if __name__ == "__main__":
    main()
