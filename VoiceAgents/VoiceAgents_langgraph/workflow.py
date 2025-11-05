"""
Main LangGraph Workflow - Connects all agent nodes
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from .state import VoiceAgentState
from .nodes.routing import route_node
from .nodes.appointment import appointment_node
from .nodes.followup import followup_node
from .nodes.medication import medication_node
from .nodes.caregiver import caregiver_node
from .nodes.help import help_node


def route_after_intent(state: VoiceAgentState) -> str:
    """Route to appropriate agent based on intent"""
    intent = state.get("intent", "help")
    return intent


def create_workflow():
    """Create and configure the LangGraph workflow"""
    
    # Create the graph
    workflow = StateGraph(VoiceAgentState)
    
    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("appointment", appointment_node)
    workflow.add_node("followup", followup_node)
    workflow.add_node("medication", medication_node)
    workflow.add_node("caregiver", caregiver_node)
    workflow.add_node("help", help_node)
    
    # Set entry point
    workflow.set_entry_point("route")
    
    # Add conditional edges from route to agents
    workflow.add_conditional_edges(
        "route",
        route_after_intent,
        {
            "appointment": "appointment",
            "followup": "followup",
            "medication": "medication",
            "caregiver": "caregiver",
            "help": "help"
        }
    )
    
    # All agent nodes end
    workflow.add_edge("appointment", END)
    workflow.add_edge("followup", END)
    workflow.add_edge("medication", END)
    workflow.add_edge("caregiver", END)
    workflow.add_edge("help", END)
    
    return workflow.compile()


# Create the compiled workflow instance
voice_agent_workflow = create_workflow()

