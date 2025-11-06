"""
Utility functions for VoiceAgents LangGraph implementation
"""
import os
import sys
import json
from functools import wraps
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timezone

# Database is now local to VoiceAgents_langgraph

# Optional TTS
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# Optional STT
try:
    import speech_recognition as sr
except Exception:
    sr = None

# Optional local Whisper (faster-whisper)
FW_AVAILABLE = False
try:
    from faster_whisper import WhisperModel  # type: ignore
    FW_AVAILABLE = True
except Exception:
    WhisperModel = None  # type: ignore
    FW_AVAILABLE = False

_FW_MODEL = None  # cached model instance

def _get_faster_whisper_model():
    global _FW_MODEL
    if not FW_AVAILABLE:
        return None
    if _FW_MODEL is None:
        # Choose a small model for speed; user can upgrade later ("small", "medium")
        _FW_MODEL = WhisperModel("base")
    return _FW_MODEL

def now_iso() -> str:
    """Return current timestamp in ISO format"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# Fallback logging directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
FALLBACK_LOG = os.path.join(LOG_DIR, "fallback_log.jsonl")


def _log_fallback(func_name: str, error: Exception, context: Optional[Dict] = None):
    """Log fallback events to fallback_log.jsonl"""
    try:
        entry = {
            "timestamp": now_iso(),
            "function": func_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        with open(FALLBACK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Silently fail if logging itself fails
        pass


def safe_call(default_message: str = "Service unavailable. Please try again later."):
    """
    Decorator for safe error handling with fallback logging.
    
    Args:
        default_message: Message to return on error
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the fallback event
                _log_fallback(
                    func.__name__,
                    e,
                    context={"args": str(args)[:200], "kwargs": str(kwargs)[:200]}
                )
                print(f"[FALLBACK] {func.__name__}: {e}")
                return default_message
        return wrapper
    return decorator


# LLM Provider (supports OpenAI, Anthropic, Google)
# Import first, then apply safe_call decorator to avoid circular import
try:
    from .llm_provider import (
        chat_completion as _chat_completion_raw,
        audio_transcribe as _audio_transcribe_raw,
        USE_LLM, LLM_PROVIDER, get_default_model)
    # Apply safe_call decorator after import
    chat_completion = safe_call(default_message=None)(_chat_completion_raw)
    audio_transcribe = safe_call(default_message=None)(_audio_transcribe_raw)
except ImportError:
    # Fallback if dotenv is not available
    USE_LLM = False
    LLM_PROVIDER = "openai"
    def chat_completion(*args, **kwargs):
        return None
    def audio_transcribe(*args, **kwargs):
        return None
    def get_default_model():
        return "gpt-4o-mini"


@safe_call(default_message="[TTS Error] Text-to-speech unavailable.")
def say(text: str, voice: bool = False):
    """Print text and optionally speak it"""
    print(f"\nAgent: {text}")
    if voice and pyttsx3 is not None:
        eng = pyttsx3.init()
        voices = eng.getProperty('voices')
        english_voice = None
        for v in voices:
            if 'english' in v.name.lower() or 'en_' in v.id.lower() or 'en-' in v.id.lower():
                english_voice = v.id
                break
            if 'david' in v.name.lower() or 'zira' in v.name.lower() or 'mark' in v.name.lower():
                english_voice = v.id
                break
        if english_voice:
            eng.setProperty('voice', english_voice)
        eng.setProperty("rate", 155)
        eng.say(text)
        eng.runAndWait()


def stt_transcribe(path: str) -> str:
    """Transcribe audio file to text"""
    if not os.path.exists(path):
        return ""

    # 1) Prefer local faster-whisper if available (robust, no quota)
    try:
        if FW_AVAILABLE:
            model = _get_faster_whisper_model()
            if model is not None:
                segments, info = model.transcribe(
                    path,
                    beam_size=5,
                    vad_filter=True,
                )
                out = []
                for seg in segments:
                    if getattr(seg, "text", ""):
                        out.append(seg.text.strip())
                text = " ".join(out).strip()
                if text:
                    return text
    except Exception:
        # fall through to other methods
        pass

    # 2) Try LLM provider audio transcription (OpenAI Whisper API)
    try:
        if USE_LLM:
            text = audio_transcribe(path)
            if text:
                return text.strip()
    except Exception:
        pass

    # 3) Fallback to speech_recognition (original behavior)
    if sr is not None:
        ext = os.path.splitext(path)[-1].lower()
        if ext in [".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a"]:
            try:
                r = sr.Recognizer()
                with sr.AudioFile(path) as source:
                    audio = r.record(source)
                try:
                    return r.recognize_google(audio)
                except Exception:
                    return ""
            except Exception:
                return ""

    return ""


def mic_listen_once(timeout=5, phrase_time_limit=10) -> str:
    """Listen to microphone once and transcribe"""
    if sr is None:
        print("❌ Speech recognition not available - install SpeechRecognition and pyaudio")
        return ""
    
    try:
        r = sr.Recognizer()
        # Improved settings for better accuracy (from original VoiceAgents)
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

