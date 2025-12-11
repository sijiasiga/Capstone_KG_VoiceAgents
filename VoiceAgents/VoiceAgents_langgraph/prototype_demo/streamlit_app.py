# streamlit_app.py
# Streamlit UI for LangGraph VoiceAgents system

import sys
import json
import tempfile
from pathlib import Path
import streamlit as st

# --- ensure parent directory is in sys.path for imports ---
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARENT = ROOT.parent

if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

# --- import LangGraph workflow ---
try:
    from VoiceAgents_langgraph.workflow import voice_agent_workflow
    from VoiceAgents_langgraph.state import VoiceAgentState
    from VoiceAgents_langgraph.nodes.routing import (
        parse_intent_llm, parse_intent_rules
    )
    from VoiceAgents_langgraph.utils import stt_transcribe, now_iso
    from VoiceAgents_langgraph.utils.logging_utils import (
        log_orchestration, setup_console_logging, log_turn_summary
    )
except Exception as e:
    st.error(f"Failed to import LangGraph workflow: {e}")
    st.stop()

# --- check STT availability ---
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

# --- constants ---
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ORCH_LOG = LOG_DIR / "orchestration_log.jsonl"


def process_message(user_text: str, patient_id: str, voice_enabled: bool, session_id: str):
    """Process user message through LangGraph workflow"""
    # Set up console logging on first call
    if not hasattr(st.session_state, '_console_logging_setup'):
        setup_console_logging()
        st.session_state._console_logging_setup = True
    
    st.session_state.chat.append({"role": "user", "text": user_text})
    
    # Initialize turn_index if not exists
    if "turn_index" not in st.session_state:
        st.session_state.turn_index = 0
    
    user_turn_idx = st.session_state.turn_index * 2  # User turns are even (0, 2, 4...)
    
    # Log user turn to console (terminal)
    log_turn_summary(
        timestamp=now_iso(),
        conversation_id=session_id,
        turn_index=user_turn_idx,
        role="user",
        message=user_text,
        input_channel="typed",  # Streamlit input is typed
    )

    intent_info = {}
    try:
        intent_info = parse_intent_llm(user_text) or {}
    except Exception:
        intent_info = parse_intent_rules(user_text) or {}
    detected_intent = intent_info.get("intent", "help")
    detected_pid = intent_info.get("patient_id") or patient_id

    initial_state: VoiceAgentState = {
        "user_input": user_text,
        "patient_id": detected_pid,
        "intent": None,
        "parsed_data": {},
        "appointment_response": None,
        "followup_response": None,
        "medication_response": None,
        "caregiver_response": None,
        "help_response": None,
        "response": None,
        "voice_enabled": voice_enabled,
        "session_id": session_id,
        "timestamp": now_iso(),
        "log_entry": None
    }

    try:
        with st.spinner("Processing..."):
            final_state = voice_agent_workflow.invoke(initial_state)
            reply = final_state.get("response", "I'm sorry, I couldn't process that request.")

        st.session_state.chat.append({
            "role": "agent",
            "text": reply,
            "intent": detected_intent,
            "pid": detected_pid
        })

        # Determine which agent responded
        intent = final_state.get("intent", "help")
        agent_name = intent if intent in ["appointment", "followup", "medication", "caregiver", "help"] else "help"
        
        # Extract provider/model info from log_entry if available
        log_entry_data = final_state.get("log_entry", {})
        provider = log_entry_data.get("provider")
        model = log_entry_data.get("model")
        actions = log_entry_data.get("actions", {})
        policies = log_entry_data.get("policies", {})
        latency_ms = log_entry_data.get("latency_ms")
        
        assistant_turn_idx = st.session_state.turn_index * 2 + 1  # Assistant turns are odd (1, 3, 5...)
        
        # TTS is not used in Streamlit (voice_enabled is False by default)
        tts_backend = None
        tts_used = 0
        
        # Log assistant turn to console (terminal)
        log_turn_summary(
            timestamp=now_iso(),
            conversation_id=session_id,
            turn_index=assistant_turn_idx,
            role="assistant",
            agent=agent_name,
            provider=provider,
            model=model,
            message=reply,
            actions=actions,
            policies=policies,
            used_llm=1 if (provider and model) else 0,
            latency_ms=latency_ms,
            tts_used=tts_used,
            tts_backend=tts_backend,
        )
        
        # Increment turn index for next turn
        st.session_state.turn_index += 1

        log_entry = {
            "ts": now_iso(),
            "agent": "OrchestrationAgent",
            "session_id": session_id,
            "input": user_text,
            "intent": final_state.get("intent"),
            "patient_id": final_state.get("patient_id"),
            "routed_reply": reply,
            "log_entry": log_entry_data
        }
        log_orchestration(log_entry)

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        st.session_state.chat.append({
            "role": "agent",
            "text": error_msg,
            "intent": "error",
            "pid": detected_pid
        })
        
        error_turn_idx = st.session_state.turn_index * 2 + 1
        
        # Log error turn to console (terminal)
        log_turn_summary(
            timestamp=now_iso(),
            conversation_id=session_id,
            turn_index=error_turn_idx,
            role="system",
            agent="error",
            error=str(e),
        )
        
        st.error(error_msg)

    st.rerun()


# --- page config ---
st.set_page_config(
    page_title="VoiceAgents",
    layout="centered",
    initial_sidebar_state="auto"
)

# Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }
    
    .block-container { padding: 2rem; max-width: 900px; }
    
    h1 {
        font-weight: 700 !important;
        font-size: 2rem !important;
        color: #1a1a1a !important;
        margin-bottom: 2rem !important;
        text-align: center;
    }
    
     .stButton > button {
         border-radius: 10px;
         font-weight: 600;
         padding: 0.75rem;
         transition: all 0.2s;
         border: 2px solid #6366f1 !important; /* indigo/purple outline */
         outline: none !important;
     }
     
     .stButton > button[kind="primary"] {
         background: linear-gradient(135deg, #6366f1, #4f46e5);
         color: white;
         box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
     }
     
     .stButton > button[kind="primary"]:focus {
         outline: none !important;
         box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.35);
     }
     
     .stTextInput input {
         border-radius: 10px !important;
         border: 2px solid #6366f1 !important; /* indigo/purple outline */
         padding: 1rem !important;
         font-size: 1rem !important;
         outline: none !important;
         box-shadow: none !important;
     }
     .stTextInput input:focus {
         border-color: #6366f1 !important;
         box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
         outline: none !important;
     }
     
     /* Force remove all red borders - override all validation states */
     input,
     input[type="text"],
     input[data-testid="textInput"],
     input:invalid,
     input:valid,
     input:required,
     input:optional,
     input:focus,
     input:active,
     input:focus:invalid,
     input:focus:valid,
     input:active:invalid,
     input:active:valid,
     input[aria-invalid="true"],
     input[aria-invalid="false"],
     .stTextInput input,
     .stTextInput input:invalid,
     .stTextInput input:valid,
     .stTextInput input:focus,
     .stTextInput input:active,
     .stTextInput input:focus:invalid,
     .stTextInput input:active:invalid {
         border-color: #6366f1 !important;
         box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
         outline: none !important;
     }
     
     /* Remove browser default validation styling */
     input:-webkit-autofill,
     input:-webkit-autofill:hover,
     input:-webkit-autofill:focus {
         border-color: #6366f1 !important;
         -webkit-box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
         box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
     }
    
    .stChatMessage {
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border: 1px solid #e5e7eb;
    }
    
    .stChatMessage[data-testid="user-message"] {
        background: linear-gradient(135deg, #eff6ff, #dbeafe);
        border-color: #bfdbfe;
    }
    
    .recording-indicator {
        background: linear-gradient(135deg, #a855f7, #9333ea);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 1rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Input controls row */
    .input-controls {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    
    /* Send button icon style */
    .send-icon {
        font-size: 1.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "chat" not in st.session_state:
    st.session_state.chat = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit_{now_iso()}"
if "compose_text" not in st.session_state:
    st.session_state.compose_text = ""
if "patient_id" not in st.session_state:
    st.session_state.patient_id = "10004235"
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False
if "show_logs" not in st.session_state:
    st.session_state.show_logs = False
if "max_logs" not in st.session_state:
    st.session_state.max_logs = 10
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

# Sidebar - persistent settings
with st.sidebar:
    st.markdown("### Settings")
    st.session_state.patient_id = st.text_input(
        "Patient ID", 
        value=st.session_state.patient_id,
        key="pid_input"
    )
    st.session_state.voice_enabled = st.toggle(
        "Enable TTS", 
        value=st.session_state.voice_enabled,
        key="tts_toggle"
    )
    
    st.markdown("---")
    st.markdown("### Logs")
    st.session_state.show_logs = st.checkbox(
        "Show logs", 
        value=st.session_state.show_logs,
        key="logs_checkbox"
    )
    if st.session_state.show_logs:
        st.session_state.max_logs = st.slider(
            "Number of logs", 
            5, 50, 
            st.session_state.max_logs,
            key="logs_slider"
        )

# Header
st.markdown("<h1>VoiceAgents</h1>", unsafe_allow_html=True)

# Conversation Area
st.markdown("### Conversation")
if st.session_state.chat:
    chat_container = st.container(height=350, border=True)
    with chat_container:
        for msg in st.session_state.chat:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["text"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["text"])
                    if msg.get("intent") or msg.get("pid"):
                        parts = []
                        if msg.get("intent"):
                            parts.append(f"`{msg['intent']}`")
                        if msg.get("pid"):
                            parts.append(f"Patient: `{msg['pid']}`")
                        st.caption(" · ".join(parts))
else:
    st.info("No messages yet. Type a message or use voice input below.")

st.markdown("<br>", unsafe_allow_html=True)

# Unified Input Area
st.markdown("### Your Message")

# Recording status indicator
if 'recording_status' not in st.session_state:
    st.session_state.recording_status = 'idle'
if 'bg_stop' not in st.session_state:
    st.session_state.bg_stop = None

if st.session_state.recording_status == 'recording':
    st.markdown('<div class="recording-indicator"><b>● RECORDING</b> - Speak now...</div>', unsafe_allow_html=True)
elif st.session_state.recording_status == 'processing':
    st.markdown('<div style="background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; padding: 0.75rem; border-radius: 8px; text-align: center; margin-bottom: 1rem;"><b>⏳ PROCESSING</b> - Transcribing...</div>', unsafe_allow_html=True)

# Text input area (shared)
compose_input = st.text_input(
    "Message",
    value=st.session_state.compose_text,
    placeholder="Type your message or record using voice...",
    label_visibility="collapsed",
    key=f"compose_{st.session_state.get('text_key', 0)}"
)

# Update session state
if compose_input != st.session_state.compose_text:
    st.session_state.compose_text = compose_input

# Input controls row - Voice and Send buttons
col1, col2 = st.columns([1, 1])

with col1:
    # Voice recording button
    if not STT_AVAILABLE:
        st.button(" Voice", disabled=True, help="Install SpeechRecognition & pyaudio")
    else:
        is_recording = st.session_state.recording_status == 'recording'
        is_processing = st.session_state.recording_status == 'processing'
        
        if is_recording:
            voice_btn = st.button("Stop", type="primary", disabled=False, use_container_width=True)
        else:
            voice_btn = st.button("Record", type="primary", disabled=is_processing, use_container_width=True)
        
        # Handle recording start
        if voice_btn and st.session_state.recording_status == 'idle':
            try:
                import speech_recognition as _sr
                r = _sr.Recognizer()
                m = _sr.Microphone(sample_rate=16000)
                with m as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)

                buf, meta = [], {"sample_rate": 16000, "sample_width": 2, "channels": 1}
                st.session_state.mic_buf = buf
                st.session_state.mic_meta = meta

                def _cb(recognizer, audio):
                    raw = audio.get_raw_data()
                    meta.update({
                        "sample_rate": int(getattr(audio, 'sample_rate', 16000)),
                        "sample_width": int(getattr(audio, 'sample_width', 2))
                    })
                    buf.append(raw)

                st.session_state.bg_stop = r.listen_in_background(m, _cb)
                st.session_state.recording_status = 'recording'
                st.rerun()
            except Exception as e:
                st.error(f"Microphone error: {e}")
        
        # Handle recording stop
        if voice_btn and st.session_state.recording_status == 'recording':
            try:
                if st.session_state.bg_stop:
                    st.session_state.bg_stop(wait_for_stop=False)
                    st.session_state.bg_stop = None
                st.session_state.recording_status = 'processing'

                chunks = st.session_state.get('mic_buf', [])
                if not chunks:
                    st.session_state.recording_status = 'idle'
                    st.warning("No audio captured")
                    st.rerun()

                tmp_path = Path(tempfile.gettempdir()) / "va_rec.wav"
                meta = st.session_state.get('mic_meta', {"sample_rate": 16000, "sample_width": 2, "channels": 1})
                
                import wave
                with wave.open(str(tmp_path), 'wb') as wf:
                    wf.setnchannels(meta.get('channels', 1))
                    wf.setsampwidth(meta.get('sample_width', 2))
                    wf.setframerate(meta.get('sample_rate', 16000))
                    for raw in chunks:
                        wf.writeframes(raw)

                transcribed = stt_transcribe(str(tmp_path))
                st.session_state.mic_buf = []
                tmp_path.unlink(missing_ok=True)

                if transcribed:
                    # Fill the input area with transcript
                    st.session_state.compose_text = transcribed
                    st.session_state.text_key = st.session_state.get('text_key', 0) + 1
                    st.session_state.recording_status = 'idle'
                    st.success(f"Transcribed: \"{transcribed}\"")
                    st.rerun()
                else:
                    st.session_state.recording_status = 'idle'
                    st.warning("Could not transcribe")
                    st.rerun()
            except Exception as e:
                st.session_state.recording_status = 'idle'
                st.error(f"Error: {e}")
                st.rerun()

with col2:
     # Send button (same size/color as others)
     if st.button("Send", type="primary", use_container_width=True, key="send_btn"):
        # Get message from current input or session state
        current_key = st.session_state.get('text_key', 0)
        input_key = f'compose_{current_key}'
        msg = st.session_state.get(input_key, '').strip()
        if not msg:
            msg = st.session_state.compose_text.strip()
        
        if msg:
            st.session_state.compose_text = ""
            st.session_state.text_key = current_key + 1
            process_message(
                msg, 
                st.session_state.patient_id, 
                st.session_state.voice_enabled, 
                st.session_state.session_id
            )
        else:
            st.warning("Please enter a message")

# Logs section
if st.session_state.show_logs:
    st.markdown("---")
    st.markdown("### System Logs")
    logs = []
    if ORCH_LOG.exists():
        try:
            with open(ORCH_LOG) as f:
                for line in f:
                    if line.strip():
                        try:
                            logs.append(json.loads(line))
                        except:
                            pass
            logs = logs[-st.session_state.max_logs:]
        except Exception as e:
            st.warning(f"Could not read logs: {e}")

    if logs:
        for rec in reversed(logs):
            ts = rec.get('ts', 'N/A')
            intent = rec.get('intent', '?')
            pid = rec.get('patient_id', 'N/A')
            
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = ts
            
            with st.expander(f"**{time_str}** · `{intent}` · Patient: `{pid}`"):
                st.json(rec, expanded=False)
    else:
        st.info("No logs yet")