"""
Help Node - Provides help information and general LLM conversation
"""
import os
import json
from ..state import VoiceAgentState
from ..utils.llm_provider import chat_completion, USE_LLM, get_default_model
from ..utils import say

# Load agent-specific policy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "help_policy.json")
AGENT_POLICY = {}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r") as f:
        AGENT_POLICY = json.load(f)
    # Log policy summary on startup
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    print(f"[Policy] Help Agent loaded: scope=[{scope_str}], triage={AGENT_POLICY.get('triage_required', False)}")


def help_node(state: VoiceAgentState) -> VoiceAgentState:
    """Help agent node - Uses LLM for natural conversation"""
    user_input = state.get("user_input", "")
    
    # Use LLM for general conversation
    if USE_LLM:
        system_prompt = """You are a helpful healthcare assistant for a voice triage system. 
You can help with:
- Appointments: scheduling, checking status, rescheduling, canceling
- Symptoms: reporting and monitoring patient symptoms
- Medications: questions about prescriptions, side effects, interactions
- Caregiver summaries: weekly patient summaries for caregivers

Be friendly, concise, and helpful. If the user asks something unrelated to healthcare or this system, 
politely redirect them to how you can help with healthcare needs."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = chat_completion(
                messages=messages, 
                temperature=0.7,
                model=get_default_model()
            )
            if response:
                state["help_response"] = response
                state["response"] = response
                # Output with TTS if enabled
                if state.get("voice_enabled", False):
                    say(response, voice=True)
                return state
        except Exception as e:
            print(f"[LLM Error in help node: {e}]")
    
    # Fallback to static help message
    response = (
        "I can help with appointments, symptoms (follow-up), medications, and caregiver summaries.\n"
        "Try something like:\n"
        "- 'I am patient 10004235, check my appointment'\n"
        "- 'I feel dizzy 7/10'\n"
        "- 'What are the side effects of metformin?'\n"
        "- 'Give me this week's caregiver update for 10001217'"
    )
    
    state["help_response"] = response
    state["response"] = response
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

