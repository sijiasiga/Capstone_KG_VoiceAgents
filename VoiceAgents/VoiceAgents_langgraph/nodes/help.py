"""
Help Node - Provides help information and general LLM conversation
"""
import os
import json
from ..state import VoiceAgentState
from ..utils.llm_provider import chat_completion, USE_LLM, get_default_model
from ..utils import say, now_iso

# Load agent-specific policy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(BASE_DIR, "..", "policy", "agents", "help_policy.json")
AGENT_POLICY = {}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r") as f:
        AGENT_POLICY = json.load(f)
    # Log policy summary on startup
    from ..utils.logging_utils import get_conversation_logger
    logger = get_conversation_logger()
    scope_str = ", ".join(AGENT_POLICY.get("scope", []))
    logger.info(f"[Policy] Help Agent loaded: scope=[{scope_str}], triage={AGENT_POLICY.get('triage_required', False)}")


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
            result = chat_completion(
                messages=messages, 
                temperature=0.7,
                model=get_default_model()
            )
            if result:
                # Handle tuple return: (text, provider, model, latency_ms) or (text, provider, model)
                if isinstance(result, tuple):
                    if len(result) == 4:
                        response, provider, model, latency_ms = result
                    else:
                        response, provider, model = result[:3]
                        latency_ms = result[3] if len(result) > 3 else None
                else:
                    response = result
                    provider = None
                    model = None
                    latency_ms = None
                if response:
                    state["help_response"] = response
                    state["response"] = response
                    
                    # Extract actions from actual execution
                    # Help agent provides general assistance, no specific action beyond responding
                    # used_llm is True if we actually got provider/model from LLM call
                    actions = {
                        "response_provided": True,
                        "used_llm": provider is not None and model is not None  # Derived from actual execution
                    }
                    
                    # Extract policies that were actually applied
                    # Help agent doesn't apply specific policies, just provides information
                    policies = {
                        "policies_applied": [],  # No specific policies applied
                        "scope": AGENT_POLICY.get("scope", []),  # Available scope from policy file
                        "triage_required": AGENT_POLICY.get("triage_required", False)  # From policy file
                    }
                    
                    # Log entry
                    log_entry = {
                        "ts": now_iso(),
                        "agent": "HelpAgent",
                        "patient_id": state.get("patient_id"),
                        "input": user_input,
                        "response": response,
                        "provider": provider,
                        "model": model,
                        "latency_ms": latency_ms,  # Store latency for conversation log
                        "actions": actions,
                        "policies": policies
                    }
                    state["log_entry"] = log_entry
                    
                # Output with TTS if enabled
                if state.get("voice_enabled", False):
                    say(response, voice=True)
                return state
        except Exception as e:
            logger = get_conversation_logger()
            logger.error(f"[LLM Error in help node: {e}]")
    
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
    
    # Log entry for fallback case
    actions = {
        "response_provided": True,
        "used_llm": False,  # Fallback doesn't use LLM
        "fallback_used": True
    }
    policies = {
        "policies_applied": [],  # No specific policies applied in fallback
        "scope": AGENT_POLICY.get("scope", []),  # Available scope from policy file
        "triage_required": AGENT_POLICY.get("triage_required", False)  # From policy file
    }
    log_entry = {
        "ts": now_iso(),
        "agent": "HelpAgent",
        "patient_id": state.get("patient_id"),
        "input": user_input,
        "response": response,
        "provider": None,  # Fallback doesn't use LLM
        "model": None,
        "actions": actions,
        "policies": policies
    }
    state["log_entry"] = log_entry
    
    # Output with TTS if enabled
    if state.get("voice_enabled", False):
        say(response, voice=True)
    
    return state

