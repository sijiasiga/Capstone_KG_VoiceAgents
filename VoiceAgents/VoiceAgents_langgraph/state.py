"""
LangGraph State Schema for VoiceAgents
"""
from typing import TypedDict, Optional, Dict, Any, List
from datetime import datetime


class VoiceAgentState(TypedDict):
    """State schema shared across all agent nodes"""
    # Input
    user_input: str
    patient_id: Optional[str]
    
    # Routing
    intent: Optional[str]  # appointment | followup | medication | caregiver | help
    
    # Parsed data
    parsed_data: Dict[str, Any]  # Intent-specific parsed data
    
    # Agent responses
    appointment_response: Optional[str]
    followup_response: Optional[str]
    medication_response: Optional[str]
    caregiver_response: Optional[str]
    help_response: Optional[str]
    
    # Final output
    response: Optional[str]
    
    # Context
    voice_enabled: bool
    session_id: Optional[str]
    timestamp: Optional[str]
    
    # Logging
    log_entry: Optional[Dict[str, Any]]

