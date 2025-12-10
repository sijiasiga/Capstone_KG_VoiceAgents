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
        # Model size from env var (defaults to "base" for speed)
        # Options: "tiny", "base", "small", "medium", "large-v2", "large-v3"
        model_size = os.getenv("FASTER_WHISPER_MODEL", "base")
        _FW_MODEL = WhisperModel(model_size)
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
        USE_LLM, get_default_model)
    # chat_completion returns tuple (text, provider, model, latency_ms) or None
    # We wrap it to handle errors but preserve the tuple return
    def chat_completion(*args, **kwargs):
        try:
            result = _chat_completion_raw(*args, **kwargs)
            # If result is a 3-tuple (old format), add latency_ms=0 for backward compatibility
            if result and isinstance(result, tuple) and len(result) == 3:
                return (*result, 0)  # Add latency_ms=0
            return result
        except Exception as e:
            from .logging_utils import get_conversation_logger
            logger = get_conversation_logger()
            logger.error(f"[FALLBACK] chat_completion: {e}")
            return None
    # audio_transcribe is used directly (returns tuple, not wrapped)
    audio_transcribe = _audio_transcribe_raw
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


def say(text: str, voice: bool = False) -> Optional[str]:
    """
    Print text and optionally speak it.
    
    Priority order:
    1. OpenAI TTS API (tts-1)
    2. Local pyttsx3
    
    Logs which backend was used.
    Returns: TTS backend name if voice=True, None otherwise
    """
    from .logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    # Log to console only (message will be in metadata line via log_turn_summary)
    # Use a different logger level or just print to console
    import sys
    print(f"\nAgent: {text}", file=sys.stdout)
    
    if not voice:
        return None
    
    backend_used = None
    tts_model = os.getenv("TTS_MODEL", "tts-1")
    
    # 1) Try OpenAI TTS API first (primary TTS)
    try:
        if USE_LLM:
            from .llm_provider import _get_openai_client
            client = _get_openai_client()
            if client is not None:
                try:
                    response = client.audio.speech.create(
                        model=tts_model,
                        voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
                        input=text,
                    )
                    # Save to temporary file and play
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        tmp_file.write(response.content)
                        tmp_path = tmp_path = tmp_file.name
                    
                    # Play audio file (platform-dependent)
                    import platform
                    import subprocess
                    system = platform.system()
                    if system == "Darwin":  # macOS
                        subprocess.run(["afplay", tmp_path], check=False)
                    elif system == "Linux":
                        subprocess.run(["aplay", tmp_path], check=False)
                    elif system == "Windows":
                        # Try pygame first (supports MP3, plays silently in background)
                        try:
                            import pygame
                            pygame.mixer.init()
                            pygame.mixer.music.load(tmp_path)
                            pygame.mixer.music.play()
                            logger.info("[TTS] Playing with pygame")
                            while pygame.mixer.music.get_busy():
                                import time
                                time.sleep(0.1)
                            logger.info("[TTS] Pygame playback completed")
                        except Exception as e_pygame:
                            logger.warning(f"[TTS] Pygame failed: {e_pygame}")
                            # Fallback: use PowerShell with Add-Type for audio playback
                            # This waits for audio to complete before continuing
                            ps_cmd = f'''
                            Add-Type -AssemblyName presentationCore
                            $mediaPlayer = New-Object System.Windows.Media.MediaPlayer
                            $mediaPlayer.Open([uri]"{tmp_path}")
                            $mediaPlayer.Play()
                            Start-Sleep -Milliseconds 500
                            while ($mediaPlayer.NaturalDuration.HasTimeSpan -eq $false) {{
                                Start-Sleep -Milliseconds 100
                            }}
                            $duration = $mediaPlayer.NaturalDuration.TimeSpan.TotalSeconds
                            Start-Sleep -Seconds $duration
                            $mediaPlayer.Stop()
                            $mediaPlayer.Close()
                            '''
                            try:
                                logger.info("[TTS] Trying PowerShell/WMPlayer")
                                result = subprocess.run(
                                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                                    check=False,
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                                )
                                if result.returncode == 0:
                                    logger.info("[TTS] PowerShell playback completed")
                                else:
                                    logger.warning(f"[TTS] PowerShell failed: {result.stderr.decode()}")
                            except Exception as e_ps:
                                logger.warning(f"[TTS] PowerShell exception: {e_ps}")
                                # Last resort: minimize the window when opening
                                logger.info("[TTS] Using start /min fallback")
                                subprocess.run(["start", "/min", tmp_path], shell=True, check=False)
                    
                    # Clean up
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    
                    backend_used = "openai_tts"
                    from .logging_utils import get_conversation_logger
                    logger = get_conversation_logger()
                    logger.info(f"[TTS] Using backend: {backend_used}")
                    return backend_used
                except Exception as e:
                    from .logging_utils import get_conversation_logger
                    logger = get_conversation_logger()
                    logger.error(f"[TTS] OpenAI TTS failed: {e}")
    except Exception as e:
        from .logging_utils import get_conversation_logger
        logger = get_conversation_logger()
        logger.error(f"[TTS] OpenAI TTS error: {e}")
    
    # 2) Fallback to local pyttsx3
    if pyttsx3 is not None:
        try:
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
            backend_used = "pyttsx3"
            from .logging_utils import get_conversation_logger
            logger = get_conversation_logger()
            logger.info(f"[TTS] Using backend: {backend_used}")
            return backend_used
        except Exception as e:
            from .logging_utils import get_conversation_logger
            logger = get_conversation_logger()
            logger.error(f"[TTS] Local pyttsx3 failed: {e}")
            logger.error("[TTS Error] Text-to-speech unavailable.")
    else:
        from .logging_utils import get_conversation_logger
        logger = get_conversation_logger()
        logger.error("[TTS Error] Text-to-speech unavailable (no pyttsx3).")
    
    return None


def stt_transcribe(path: str) -> str:
    """
    Transcribe audio file to text.
    
    Priority order:
    1. OpenAI Whisper API (whisper-1)
    2. Local faster-whisper
    
    Returns transcription text. Logs which backend was used.
    """
    from .logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    
    if not os.path.exists(path):
        return ""

    backend_used = None
    text = None

    # 1) Try OpenAI Whisper API first (primary ASR)
    # Note: audio_transcribe() internally checks if OpenAI is available
    try:
        if USE_LLM:
            result = audio_transcribe(path)
            if result is not None:
                text, backend_used = result
                if text:
                    # Backend already logged in audio_transcribe()
                    return text.strip()
    except Exception as e:
        from .logging_utils import get_conversation_logger
        logger = get_conversation_logger()
        logger.error(f"[ASR] OpenAI Whisper failed: {e}")

    # 2) Fallback to local faster-whisper
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
                    backend_used = "local_faster_whisper"
                    from .logging_utils import get_conversation_logger
                    logger = get_conversation_logger()
                    logger.info(f"[ASR] Using backend: local_faster_whisper")
                    return text
    except Exception as e:
        from .logging_utils import get_conversation_logger
        logger = get_conversation_logger()
        logger.error(f"[ASR] Local faster-whisper failed: {e}")

    # 3) Last resort: Google Speech Recognition (optional fallback)
    if sr is not None:
        ext = os.path.splitext(path)[-1].lower()
        if ext in [".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a"]:
            try:
                r = sr.Recognizer()
                with sr.AudioFile(path) as source:
                    audio = r.record(source)
                try:
                    text = r.recognize_google(audio)
                    backend_used = "google_stt"
                    print(f"[ASR] Using backend: {backend_used}")
                    return text
                except Exception:
                    pass
            except Exception:
                pass

    if backend_used is None:
        print("[ASR] All transcription methods failed")
    return ""


def mic_listen_once(timeout=5, phrase_time_limit=10) -> str:
    """
    Listen to microphone once and transcribe using Whisper (same priority as stt_transcribe).
    
    Priority order:
    1. OpenAI Whisper API (whisper-1)
    2. Local faster-whisper
    3. Google Speech Recognition (last resort fallback)
    """
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
        
        # Save audio to temporary file for Whisper processing
        import tempfile
        import wave
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Write audio data to WAV file
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(audio.sample_width)
                wf.setframerate(audio.sample_rate)
                wf.writeframes(audio.get_raw_data())
            
            # Use the same Whisper pipeline as stt_transcribe()
            text = stt_transcribe(tmp_path)
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            
            if text:
                return text
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            print(f"[ASR] Whisper transcription failed: {e}")
        
        # Last resort: Google Speech Recognition (only if Whisper failed)
        try:
            text = r.recognize_google(audio, language='en-US', show_all=False)
            print("[ASR] Using backend: google_speech_recognition (fallback)")
            return text
        except Exception:
            try:
                text = r.recognize_google(audio)
                print("[ASR] Using backend: google_speech_recognition (fallback)")
                return text
            except Exception:
                pass
        
        print("[ASR] All transcription methods failed")
        return ""
        
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

