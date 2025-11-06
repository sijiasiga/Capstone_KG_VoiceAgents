"""
Simplified regression tests for VoiceAgents LangGraph workflow
Fast tests that verify core functionality without extensive LLM calls
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from VoiceAgents_langgraph.workflow import voice_agent_workflow  # noqa: E402
from VoiceAgents_langgraph.state import VoiceAgentState  # noqa: E402


def create_test_state(user_input: str,
                      patient_id: str = "10004235") -> VoiceAgentState:
    """Helper to create test state"""
    return {
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
        "voice_enabled": False,
        "session_id": "test_session",
        "timestamp": None,
        "log_entry": None
    }


class TestWorkflow:
    """Simplified workflow tests - verify system works"""

    def test_workflow_completes(self):
        """Test that workflow completes without errors"""
        state = create_test_state("hello")
        result = voice_agent_workflow.invoke(state)
        assert result is not None
        assert result.get("response") is not None

    def test_routing_appointment(self):
        """Test routing to appointment agent"""
        state = create_test_state(
            "check my appointment", patient_id="10004235")
        result = voice_agent_workflow.invoke(state)
        assert result["intent"] == "appointment"
        assert result.get("response") is not None

    def test_routing_followup(self):
        """Test routing to followup agent"""
        state = create_test_state("I feel dizzy")
        result = voice_agent_workflow.invoke(state)
        assert result["intent"] == "followup"
        assert result.get("response") is not None

    def test_red_flag_detection(self):
        """Test RED flag detection (critical safety check)"""
        state = create_test_state("I have chest pain")
        result = voice_agent_workflow.invoke(state)
        assert result.get("response") is not None
        # RED flags trigger emergency (works with rule-based logic)
        response_upper = result.get("response", "").upper()
        assert ("RED" in response_upper or
                "emergency" in response_upper or
                "911" in result.get("response", "")), \
            "RED flag should trigger emergency response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
