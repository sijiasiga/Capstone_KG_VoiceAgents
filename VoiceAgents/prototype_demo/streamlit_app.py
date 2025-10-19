# streamlit_app.py
# Streamlit UI for the multi-agent orchestration system

import os
import sys
import json
from pathlib import Path
import streamlit as st

# --- ensure project root is in sys.path ---
ROOT = Path(__file__).resolve().parents[1]  # .../VoiceAgents
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- import Orchestrator ---
try:
    from orchestration_agent.demos.orchestration_agent_workflow import (
        Orchestrator,
        parse_intent_llm,
        parse_intent_rules,
        mic_listen_once,
        stt_transcribe,
    )
except Exception as e:
    st.error(f"Failed to import Orchestrator: {e}")
    st.stop()

# --- check STT availability ---
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except:
    STT_AVAILABLE = False

# --- constants ---
LOG_DIR = ROOT / "orchestration_agent" / "demos" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ORCH_LOG = LOG_DIR / "orchestration_log.jsonl"

# --- page config ---
st.set_page_config(page_title="VoiceAgents Orchestrator Demo", layout="wide")
st.title("VoiceAgents Orchestrator Demo")

# --- sidebar ---
with st.sidebar:
    st.subheader("Settings")
    default_pid = st.text_input("Default patient_id (8 digits)", value="10004235")
    tts_on = st.toggle("Enable TTS (agent decides real playback)", value=False)
    st.caption("Note: TTS depends on local audio configuration in each agent.")
    st.divider()

    # Voice input section
    st.subheader("Microphone Voice Input")
    if STT_AVAILABLE:
        st.success("Speech recognition available")

        # Instructions with tips
        st.info("""**How to use:** Click 'Start Recording', speak clearly when you see 'LISTENING', system auto-stops after 10 seconds or when you pause.

**Tips for better accuracy:**
- Speak at normal volume, not too loud or quiet
- Pronounce each word clearly
- Pause briefly between words
- Minimize background noise
- Speak closer to the microphone (6-12 inches)
- Wait 1-2 seconds after clicking before speaking (system is calibrating)
        """)

        # Recording state management
        if 'recording_status' not in st.session_state:
            st.session_state.recording_status = 'idle'  # idle, listening, processing

        col1, col2 = st.columns(2)

        with col1:
            start_recording = st.button("Start Recording", type="primary", use_container_width=True,
                                       disabled=(st.session_state.recording_status != 'idle'))

        with col2:
            if st.session_state.recording_status != 'idle':
                status_text = "LISTENING..." if st.session_state.recording_status == 'listening' else "Processing..."
                st.markdown(f"### :red[{status_text}]")

        uploaded_audio = st.file_uploader("Or upload audio file (.wav, .mp3)", type=["wav", "mp3", "m4a", "flac"])

        if start_recording:
            st.session_state.recording_status = 'listening'
            st.rerun()

        # Handle recording in progress
        if st.session_state.recording_status == 'listening':
            try:
                transcribed = mic_listen_once(timeout=5, phrase_time_limit=10)
                st.session_state.recording_status = 'idle'

                if transcribed:
                    st.session_state.voice_input = transcribed
                    st.success(f"**Heard:** {transcribed}")
                    st.balloons()
                else:
                    st.warning("No speech detected. Please try again and speak clearly.")
            except Exception as e:
                st.session_state.recording_status = 'idle'
                error_msg = str(e)
                # Remove emoji from error message to avoid encoding issues
                error_msg = error_msg.encode('ascii', 'ignore').decode('ascii')
                st.error(f"**Microphone error:** {error_msg}\n\n**Troubleshooting:**\n- Check microphone permissions in Windows Settings\n- Ensure microphone is not used by another app\n- Try speaking louder and closer to mic")
            st.rerun()

        if uploaded_audio:
            with st.spinner("Processing audio file..."):
                try:
                    # Save temp file
                    import tempfile
                    temp_dir = Path(tempfile.gettempdir())
                    temp_path = temp_dir / uploaded_audio.name
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_audio.read())

                    transcribed = stt_transcribe(str(temp_path))
                    if transcribed:
                        st.session_state.voice_input = transcribed
                        st.success(f"Transcribed: {transcribed}")
                    else:
                        st.warning("Could not transcribe audio.")
                except Exception as e:
                    st.error(f"Audio processing error: {e}")
    else:
        st.warning("⚠️ Speech recognition not available")
        st.caption("Install: `pip install SpeechRecognition pyaudio`")

    st.divider()
    show_logs = st.checkbox("Show recent orchestration logs", value=True)
    max_logs = st.slider("Number of logs to show", 5, 200, 30)
    st.caption("To enable LLM, set OPENAI_API_KEY before running Streamlit.")

# --- initialize orchestrator ---
if "orch" not in st.session_state:
    st.session_state.orch = Orchestrator(voice=tts_on)
    st.session_state.orch.patient_id = default_pid
    st.session_state.chat = []

st.session_state.orch.voice = tts_on
st.session_state.orch.patient_id = default_pid

# --- chat history display ---
chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat:
        role = "You" if msg["role"] == "user" else "Agent"
        st.markdown(f"**{role}:** {msg['text']}")
        if msg["role"] == "agent":
            meta = []
            if msg.get("intent"):
                meta.append(f"intent: `{msg['intent']}`")
            if msg.get("pid"):
                meta.append(f"patient_id: `{msg['pid']}`")
            if meta:
                st.caption(" | ".join(meta))

# --- check for voice input ---
if "voice_input" in st.session_state and st.session_state.voice_input:
    user_text = st.session_state.voice_input
    st.session_state.voice_input = None  # Clear after use
    # Process voice input
    st.session_state.chat.append({"role": "user", "text": f"🎤 {user_text}"})

    # parse intent
    intent_info = {}
    try:
        intent_info = parse_intent_llm(user_text) or {}
    except Exception:
        intent_info = parse_intent_rules(user_text) or {}
    detected_intent = intent_info.get("intent", "help")
    detected_pid = intent_info.get("patient_id") or default_pid

    # route to appropriate agent
    try:
        reply = st.session_state.orch.route(user_text)
    except Exception as e:
        reply = f"Error during routing: {e}"

    st.session_state.chat.append({
        "role": "agent",
        "text": reply,
        "intent": detected_intent,
        "pid": detected_pid
    })
    st.rerun()

# --- input box ---
user_text = st.chat_input("Type a message, for example: 'I am patient 10004235, can you check my appointment?'")
if user_text:
    st.session_state.chat.append({"role": "user", "text": user_text})

    # parse intent
    intent_info = {}
    try:
        intent_info = parse_intent_llm(user_text) or {}
    except Exception:
        intent_info = parse_intent_rules(user_text) or {}
    detected_intent = intent_info.get("intent", "help")
    detected_pid = intent_info.get("patient_id") or default_pid

    # route to appropriate agent
    try:
        reply = st.session_state.orch.route(user_text)
    except Exception as e:
        reply = f"Error during routing: {e}"

    st.session_state.chat.append({
        "role": "agent",
        "text": reply,
        "intent": detected_intent,
        "pid": detected_pid
    })
    st.rerun()


# --- logs ---
if show_logs:
    st.divider()
    st.subheader("Recent Orchestration Logs")
    logs = []
    if ORCH_LOG.exists():
        try:
            with open(ORCH_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        logs.append(json.loads(line))
                    except Exception:
                        continue
            logs = logs[-max_logs:]
        except Exception as e:
            st.warning(f"Could not read logs: {e}")

    if logs:
        for rec in reversed(logs):
            with st.expander(f"{rec.get('ts','')} | intent: {rec.get('intent')} | patient_id: {rec.get('patient_id')}"):
                st.json(rec)
    else:
        st.caption("No logs available yet. Send a message above to start the conversation.")
