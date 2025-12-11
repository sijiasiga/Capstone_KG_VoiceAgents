"""
Main CLI entry point for LangGraph VoiceAgents
Can be run directly: python main.py
Or as module: python -m VoiceAgents_langgraph.main (from parent)
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Adjust path if running directly (python main.py) from inside VoiceAgents_langgraph/ directory
if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).resolve().parent
    # If running directly from inside the package directory, add parent to path
    PARENT_DIR = SCRIPT_DIR.parent
    if str(PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(PARENT_DIR))
    # Use absolute imports when running directly
    from VoiceAgents_langgraph.workflow import voice_agent_workflow
    from VoiceAgents_langgraph.state import VoiceAgentState
    from VoiceAgents_langgraph.utils import say, stt_transcribe, mic_listen_once, now_iso
    from VoiceAgents_langgraph.utils.logging_utils import (
        log_orchestration, setup_console_logging, log_turn_summary
    )
else:
    # Running as module (from parent directory) - use relative imports
    from .workflow import voice_agent_workflow
    from .state import VoiceAgentState
    from .utils import say, stt_transcribe, mic_listen_once, now_iso
    from .utils.logging_utils import (
        log_orchestration, setup_console_logging, log_turn_summary
    )


def main():
    """Main CLI interface"""
    # Set up console logging (terminal output only)
    setup_console_logging()
    
    print("LangGraph VoiceAgents Orchestrator")
    print("Commands:")
    print("  :voice on | :voice off            -> toggle TTS")
    print("  pid <8digit>                       -> set default patient_id context")
    print("  :stt <path_to_audio.wav/mp3>      -> transcribe then route")
    print("  :mic on                            -> speak one sentence to route")
    print("  quit                               -> exit")
    
    voice_enabled = False
    patient_id = "10004235"
    session_id = f"session_{datetime.now().timestamp()}"
    turn_index = 0  # Track conversation turns
    
    while True:
        user = input("\nYou (or command): ").strip()
        low = user.lower()
        
        if low == "quit":
            break
        elif low.startswith(":voice "):
            arg = low.split(" ", 1)[1].strip()
            voice_enabled = (arg == "on")
            print(f"[voice] {'Enabled' if voice_enabled else 'Disabled'}")
        elif low.startswith("pid "):
            patient_id = user.split(" ", 1)[1].strip()
            print(f"[context] patient_id set to {patient_id}")
        elif low.startswith(":stt "):
            path = user.split(" ", 1)[1].strip().strip('"')
            if not os.path.exists(path):
                print(f"[stt] file not found: {path}")
                continue
            print(f"[stt] transcribing: {path} ...")
            text = stt_transcribe(path)
            if not text:
                print("[stt] transcription failed.")
                continue
            print(f"[stt] → {text}")
            # Process through workflow
            process_input(text, patient_id, voice_enabled, session_id)
        elif low == ":mic on":
            text = mic_listen_once()
            if not text:
                print("[mic] no speech detected.")
                continue
            print(f"[mic→stt] {text}")
            process_input(text, patient_id, voice_enabled, session_id, turn_index)
            turn_index += 1
        else:
            process_input(user, patient_id, voice_enabled, session_id, turn_index)
            turn_index += 1


def process_input(user_input: str, patient_id: str, voice_enabled: bool, session_id: str, turn_index: int):
    """Process user input through the LangGraph workflow"""
    user_turn_idx = turn_index * 2  # User turns are even (0, 2, 4...)
    
    # Log user turn to console (terminal)
    log_turn_summary(
        timestamp=now_iso(),
        conversation_id=session_id,
        turn_index=user_turn_idx,
        role="user",
        message=user_input,
        input_channel="typed",  # CLI is always typed input
    )
    
    # Initialize state
    initial_state: VoiceAgentState = {
        "user_input": user_input,
        "patient_id": patient_id,
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
    
    # Run workflow
    try:
        final_state = voice_agent_workflow.invoke(initial_state)
        
        # Get response
        response = final_state.get("response", "I'm sorry, I couldn't process that request.")
        
        # Determine which agent responded
        intent = final_state.get("intent", "help")
        agent_name = intent if intent in ["appointment", "followup", "medication", "caregiver", "help"] else "help"
        
        # Extract provider/model info from log_entry if available
        log_entry = final_state.get("log_entry", {})
        provider = log_entry.get("provider")
        model = log_entry.get("model")
        actions = log_entry.get("actions", {})
        policies = log_entry.get("policies", {})
        latency_ms = log_entry.get("latency_ms")  # Extract latency if stored
        
        assistant_turn_idx = turn_index * 2 + 1  # Assistant turns are odd (1, 3, 5...)
        
        # Output response and get TTS backend
        tts_backend = say(response, voice_enabled)
        tts_used = 1 if tts_backend else 0
        
        # Log assistant turn to console (terminal) (includes message)
        log_turn_summary(
            timestamp=now_iso(),
            conversation_id=session_id,
            turn_index=assistant_turn_idx,
            role="assistant",
            agent=agent_name,
            provider=provider,
            model=model,
            message=response,  # Include response message in metadata line
            actions=actions,
            policies=policies,
            used_llm=1 if (provider and model) else 0,
            latency_ms=latency_ms,
            tts_used=tts_used,
            tts_backend=tts_backend,
        )
        
        # Log orchestration event (backward compatible)
        orchestration_entry = {
            "ts": now_iso(),
            "agent": "OrchestrationAgent",
            "session_id": session_id,
            "input": user_input,
            "intent": intent,
            "patient_id": final_state.get("patient_id"),
            "routed_reply": response,
            "log_entry": log_entry
        }
        log_orchestration(orchestration_entry)
        
    except Exception as e:
        error_msg = f"[ERROR] {str(e)}"
        from ..utils.logging_utils import get_conversation_logger
        logger = get_conversation_logger()
        logger.error(error_msg)
        
        error_turn_idx = turn_index * 2 + 1
        
        # Log error turn to console (terminal)
        log_turn_summary(
            timestamp=now_iso(),
            conversation_id=session_id,
            turn_index=error_turn_idx,
            role="system",
            agent="error",
            error=str(e),
        )
        
        log_orchestration({
            "ts": now_iso(),
            "agent": "OrchestrationAgent",
            "session_id": session_id,
            "input": user_input,
            "error": str(e)
        })


if __name__ == "__main__":
    main()

