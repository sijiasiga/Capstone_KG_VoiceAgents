"""
Validation Dataset Generator
Generates 50-100 test cases for Appointment and Medication agents
Executes them through the actual agent code and captures responses
Exports to CSV for client validation
"""

import os
import sys
import csv
import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Set up imports similar to main.py
if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = SCRIPT_DIR.parent
    if str(PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(PARENT_DIR))
    # Use absolute imports
    from VoiceAgents_langgraph.workflow import voice_agent_workflow
    from VoiceAgents_langgraph.state import VoiceAgentState
    from VoiceAgents_langgraph.nodes.appointment import parse_patient_input, triage_category
    from VoiceAgents_langgraph.nodes.medication import llm_parse_query, llm_score_risk

# Output directory
OUTPUT_DIR = Path(__file__).resolve().parent / "validation_datasets"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================================
# APPOINTMENT AGENT TEST CASES
# ============================================================================

APPOINTMENT_TEST_CASES = [
    # --- Check Status ---
    {"patient_id": "10004235", "input": "What's my appointment?", "category": "Check Status", "expected_intent": "check_status"},
    {"patient_id": "10004235", "input": "Can you tell me when my next appointment is?", "category": "Check Status", "expected_intent": "check_status"},
    {"patient_id": "10004235", "input": "Do I have an appointment scheduled?", "category": "Check Status", "expected_intent": "check_status"},
    {"patient_id": "10000032", "input": "Check my appointment status", "category": "Check Status", "expected_intent": "check_status"},
    {"patient_id": "10000032", "input": "When is my next visit?", "category": "Check Status", "expected_intent": "check_status"},

    # --- Reschedule (Normal) ---
    {"patient_id": "10004235", "input": "I need to reschedule my appointment", "category": "Reschedule - Normal", "expected_intent": "reschedule"},
    {"patient_id": "10004235", "input": "Can I change my appointment to next Thursday?", "category": "Reschedule - Normal", "expected_intent": "reschedule"},
    {"patient_id": "10004235", "input": "I want to move my appointment to a different day", "category": "Reschedule - Normal", "expected_intent": "reschedule"},
    {"patient_id": "10004235", "input": "Can you reschedule me for October 10 at 2pm?", "category": "Reschedule - Normal", "expected_intent": "reschedule"},

    # --- Cancel ---
    {"patient_id": "10004235", "input": "I need to cancel my appointment", "category": "Cancel", "expected_intent": "cancel"},
    {"patient_id": "10004235", "input": "Can you cancel my appointment please?", "category": "Cancel", "expected_intent": "cancel"},
    {"patient_id": "10000032", "input": "I want to cancel my upcoming visit", "category": "Cancel", "expected_intent": "cancel"},

    # --- Schedule New ---
    {"patient_id": "10004235", "input": "I want to schedule a new appointment", "category": "Schedule New", "expected_intent": "schedule_new"},
    {"patient_id": "10004235", "input": "Can I book an appointment?", "category": "Schedule New", "expected_intent": "schedule_new"},

    # --- RED FLAG: Chest Pain ---
    {"patient_id": "10004235", "input": "I'm having chest pain and need to reschedule", "category": "Triage - RED (Chest Pain)", "expected_intent": "reschedule", "expected_triage": "RED"},
    {"patient_id": "10004235", "input": "I need an appointment, I have pain in my chest", "category": "Triage - RED (Chest Pain)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "Can I schedule? My chest feels tight", "category": "Triage - RED (Chest Pain)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10004235", "input": "Tightness in my chest, when can I come in?", "category": "Triage - RED (Chest Pain)", "expected_intent": "schedule_new", "expected_triage": "RED"},

    # --- RED FLAG: Shortness of Breath ---
    {"patient_id": "10004235", "input": "I'm having trouble breathing, need appointment", "category": "Triage - RED (SOB)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "Short of breath, can I reschedule to come sooner?", "category": "Triage - RED (SOB)", "expected_intent": "reschedule", "expected_triage": "RED"},
    {"patient_id": "10004235", "input": "I'm experiencing shortness of breath", "category": "Triage - RED (SOB)", "expected_intent": "general", "expected_triage": "RED"},

    # --- RED FLAG: High Fever ---
    {"patient_id": "10004235", "input": "I have a fever of 102, need to see doctor", "category": "Triage - RED (High Fever)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10001217", "input": "My temperature is 103, can I get appointment?", "category": "Triage - RED (High Fever)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "Fever of 101.6, need appointment", "category": "Triage - RED (High Fever)", "expected_intent": "schedule_new", "expected_triage": "RED"},

    # --- RED FLAG: Severe Pain ---
    {"patient_id": "10004235", "input": "I'm in severe pain, level 9 out of 10", "category": "Triage - RED (Severe Pain)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "Pain is 10/10, unbearable, need help", "category": "Triage - RED (Severe Pain)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10004235", "input": "Extreme pain, can barely move, 8 out of 10", "category": "Triage - RED (Severe Pain)", "expected_intent": "schedule_new", "expected_triage": "RED"},

    # --- RED FLAG: Wound Issues ---
    {"patient_id": "10000032", "input": "My incision is opening up, need appointment", "category": "Triage - RED (Wound Dehiscence)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "I see yellow drainage from my wound", "category": "Triage - RED (Wound Dehiscence)", "expected_intent": "general", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "The surgical site has pus coming out", "category": "Triage - RED (Wound Dehiscence)", "expected_intent": "general", "expected_triage": "RED"},

    # --- RED FLAG: Neurological ---
    {"patient_id": "10004235", "input": "I have numbness in my arm, need appointment", "category": "Triage - RED (Neuro)", "expected_intent": "schedule_new", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "Experiencing weakness and slurred speech", "category": "Triage - RED (Neuro)", "expected_intent": "general", "expected_triage": "RED"},
    {"patient_id": "10004235", "input": "I fainted earlier today", "category": "Triage - RED (Syncope)", "expected_intent": "general", "expected_triage": "RED"},

    # --- ORANGE FLAG: Moderate Pain ---
    {"patient_id": "10004235", "input": "I have pain around 6 out of 10, can I schedule?", "category": "Triage - ORANGE (Moderate Pain)", "expected_intent": "schedule_new", "expected_triage": "ORANGE"},
    {"patient_id": "10001217", "input": "Pain level is 5, not terrible but persistent", "category": "Triage - ORANGE (Moderate Pain)", "expected_intent": "general", "expected_triage": "ORANGE"},
    {"patient_id": "10000032", "input": "Moderate pain, about 7/10, need appointment", "category": "Triage - ORANGE (Moderate Pain)", "expected_intent": "schedule_new", "expected_triage": "ORANGE"},

    # --- ORANGE FLAG: Low Fever ---
    {"patient_id": "10004235", "input": "I have a fever of 100 degrees", "category": "Triage - ORANGE (Low Fever)", "expected_intent": "general", "expected_triage": "ORANGE"},
    {"patient_id": "10001217", "input": "Temperature is 101, should I come in?", "category": "Triage - ORANGE (Low Fever)", "expected_intent": "general", "expected_triage": "ORANGE"},
    {"patient_id": "10000032", "input": "Low grade fever of 99.8, need appointment", "category": "Triage - ORANGE (Low Fever)", "expected_intent": "schedule_new", "expected_triage": "ORANGE"},

    # --- ORANGE FLAG: Dizziness ---
    {"patient_id": "10004235", "input": "I've been feeling dizzy, want to schedule", "category": "Triage - ORANGE (Dizziness)", "expected_intent": "schedule_new", "expected_triage": "ORANGE"},
    {"patient_id": "10000032", "input": "Experiencing dizziness for past 2 days", "category": "Triage - ORANGE (Dizziness)", "expected_intent": "general", "expected_triage": "ORANGE"},

    # --- ORANGE FLAG: Wound Concerns ---
    {"patient_id": "10000032", "input": "My wound has some redness around it", "category": "Triage - ORANGE (Wound Redness)", "expected_intent": "general", "expected_triage": "ORANGE"},
    {"patient_id": "10000032", "input": "There's swelling near the incision site", "category": "Triage - ORANGE (Wound Swelling)", "expected_intent": "general", "expected_triage": "ORANGE"},

    # --- POLICY: Minor Consent ---
    {"patient_id": "10001217", "input": "I want to reschedule my appointment", "category": "Policy - Minor Consent", "expected_intent": "reschedule", "policy_check": "caregiver_required"},
    {"patient_id": "10001217", "input": "Can I schedule a new appointment? I'm 17", "category": "Policy - Minor Consent", "expected_intent": "schedule_new", "policy_check": "caregiver_required"},
    {"patient_id": "10001217", "input": "Need to cancel my visit", "category": "Policy - Minor Consent", "expected_intent": "cancel", "policy_check": "caregiver_required"},

    # --- POLICY: Referral Required (HMO_A) ---
    {"patient_id": "10000032", "input": "I want to reschedule my cardiac bypass surgery", "category": "Policy - Referral Required", "expected_intent": "reschedule", "policy_check": "referral_required"},
    {"patient_id": "10001217", "input": "Can I schedule a consultation? Patient ID 10001217", "category": "Policy - Referral Required", "expected_intent": "schedule_new", "policy_check": "referral_required"},

    # --- POLICY: Telehealth Request ---
    {"patient_id": "10004235", "input": "Can I do my cardiology follow-up via video?", "category": "Policy - Telehealth Allowed", "expected_intent": "reschedule", "policy_check": "telehealth_allowed"},
    {"patient_id": "10001217", "input": "I want a video appointment for diabetes consultation", "category": "Policy - Telehealth Allowed", "expected_intent": "schedule_new", "policy_check": "telehealth_allowed"},

    # --- POLICY: Business Rules (Surgery within 48hrs) ---
    {"patient_id": "10000032", "input": "I need to reschedule my surgery that's tomorrow", "category": "Business Rule - Surgery <48hrs", "expected_intent": "reschedule", "policy_check": "surgery_48hr_rule"},

    # --- POLICY: High Urgency ---
    {"patient_id": "10000032", "input": "Can I reschedule my high urgency appointment?", "category": "Business Rule - High Urgency", "expected_intent": "reschedule", "policy_check": "high_urgency_approval"},

    # --- Natural Language Variations ---
    {"patient_id": "10004235", "input": "Hey, what time is my appointment again?", "category": "NL Variation - Casual", "expected_intent": "check_status"},
    {"patient_id": "10004235", "input": "Appointment check please", "category": "NL Variation - Brief", "expected_intent": "check_status"},
    {"patient_id": "10004235", "input": "Could you please help me reschedule my upcoming appointment to a more convenient time?", "category": "NL Variation - Formal", "expected_intent": "reschedule"},
    {"patient_id": "10004235", "input": "Move my appt pls", "category": "NL Variation - Abbreviated", "expected_intent": "reschedule"},
    {"patient_id": "10000032", "input": "I won't be able to make it to my appointment, can we cancel?", "category": "NL Variation - Explanatory", "expected_intent": "cancel"},
    {"patient_id": "10004235", "input": "Need appt ASAP", "category": "NL Variation - Urgent", "expected_intent": "schedule_new"},

    # --- Edge Cases ---
    {"patient_id": None, "input": "I want to schedule an appointment", "category": "Edge Case - No Patient ID", "expected_intent": "schedule_new"},
    {"patient_id": "99999999", "input": "Check my appointment", "category": "Edge Case - Invalid Patient ID", "expected_intent": "check_status"},
    {"patient_id": "10004235", "input": "Hello", "category": "Edge Case - General Greeting", "expected_intent": "general"},
    {"patient_id": "10004235", "input": "What services do you offer?", "category": "Edge Case - Out of Scope", "expected_intent": "general"},

    # --- Multiple Concerns ---
    {"patient_id": "10004235", "input": "I have chest pain AND I need to reschedule", "category": "Multiple Concerns - Emergency + Admin", "expected_intent": "reschedule", "expected_triage": "RED"},
    {"patient_id": "10000032", "input": "Can I reschedule? Also I'm feeling dizzy", "category": "Multiple Concerns - Admin + Symptom", "expected_intent": "reschedule", "expected_triage": "ORANGE"},
]


# ============================================================================
# MEDICATION AGENT TEST CASES
# ============================================================================

MEDICATION_TEST_CASES = [
    # --- Side Effects ---
    {"patient_id": "10004235", "input": "What are the side effects of Metformin?", "category": "Side Effects - Direct", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "I'm taking Metformin, what should I watch out for?", "category": "Side Effects - Indirect", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Will Furosemide make me dizzy?", "category": "Side Effects - Specific", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10000032", "input": "What are the common side effects of Aspirin?", "category": "Side Effects - Common", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10001217", "input": "Does Insulin have any side effects?", "category": "Side Effects - General", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "I feel nauseous after taking my medication", "category": "Side Effects - Symptom Report", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Is nausea normal with Metformin?", "category": "Side Effects - Normal?", "expected_intent": "side_effect", "expected_risk": "GREEN"},

    # --- Missed Dose (ORANGE) ---
    {"patient_id": "10004235", "input": "I forgot to take my Metformin this morning", "category": "Missed Dose - Simple", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "I missed my dose of Furosemide yesterday", "category": "Missed Dose - Previous Day", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},
    {"patient_id": "10000032", "input": "What should I do if I forget to take Aspirin?", "category": "Missed Dose - Hypothetical", "expected_intent": "missed_dose", "expected_risk": "GREEN"},
    {"patient_id": "10001217", "input": "I didn't take my Insulin this morning", "category": "Missed Dose - Insulin", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "Forgot my meds today, what now?", "category": "Missed Dose - Casual", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "I skipped my medication by accident", "category": "Missed Dose - Accidental", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},

    # --- Double Dose (RED) ---
    {"patient_id": "10004235", "input": "I accidentally took two doses of Metformin", "category": "Double Dose - RED", "expected_intent": "double_dose", "expected_risk": "RED"},
    {"patient_id": "10004235", "input": "I took my Furosemide twice by mistake", "category": "Double Dose - RED", "expected_intent": "double_dose", "expected_risk": "RED"},
    {"patient_id": "10000032", "input": "I think I took my Aspirin twice today", "category": "Double Dose - RED", "expected_intent": "double_dose", "expected_risk": "RED"},
    {"patient_id": "10001217", "input": "I injected Insulin twice this morning", "category": "Double Dose - RED", "expected_intent": "double_dose", "expected_risk": "RED"},
    {"patient_id": "10004235", "input": "Took double dose by accident", "category": "Double Dose - Brief", "expected_intent": "double_dose", "expected_risk": "RED"},

    # --- Drug Interactions (ORANGE) ---
    {"patient_id": "10004235", "input": "Can I take Metformin with Furosemide?", "category": "Drug Interaction - Patient Meds", "expected_intent": "interaction_check", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "Is it safe to take Metformin with alcohol?", "category": "Drug Interaction - Alcohol", "expected_intent": "interaction_check", "expected_risk": "ORANGE"},
    {"patient_id": "10000032", "input": "Can I take ibuprofen with Aspirin?", "category": "Drug Interaction - OTC", "expected_intent": "interaction_check", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "Are there any interactions with my medications?", "category": "Drug Interaction - General", "expected_intent": "interaction_check", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "What drugs should I avoid while taking Furosemide?", "category": "Drug Interaction - Avoid", "expected_intent": "interaction_check", "expected_risk": "ORANGE"},

    # --- Instructions (Food, Timing) ---
    {"patient_id": "10004235", "input": "Should I take Metformin with food?", "category": "Instructions - Food", "expected_intent": "instruction", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "When should I take Furosemide?", "category": "Instructions - Timing", "expected_intent": "instruction", "expected_risk": "GREEN"},
    {"patient_id": "10000032", "input": "Can I take Aspirin on an empty stomach?", "category": "Instructions - Empty Stomach", "expected_intent": "instruction", "expected_risk": "GREEN"},
    {"patient_id": "10001217", "input": "When do I inject Insulin?", "category": "Instructions - Injection Timing", "expected_intent": "instruction", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "How should I take my medications?", "category": "Instructions - General", "expected_intent": "instruction", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Best time to take my meds?", "category": "Instructions - Best Time", "expected_intent": "instruction", "expected_risk": "GREEN"},

    # --- Contraindications ---
    {"patient_id": "10004235", "input": "Can I take Metformin if I have kidney problems?", "category": "Contraindication - Renal", "expected_intent": "contraindication", "expected_risk": "ORANGE"},
    {"patient_id": "10000032", "input": "Is Aspirin safe during pregnancy?", "category": "Contraindication - Pregnancy", "expected_intent": "contraindication", "expected_risk": "ORANGE"},
    {"patient_id": "10004235", "input": "I have liver disease, can I take Metformin?", "category": "Contraindication - Hepatic", "expected_intent": "contraindication", "expected_risk": "ORANGE"},
    {"patient_id": "10001217", "input": "Is Insulin safe for pregnant women?", "category": "Contraindication - Pregnancy Safe", "expected_intent": "contraindication", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Are there conditions where I shouldn't take this?", "category": "Contraindication - General", "expected_intent": "contraindication", "expected_risk": "GREEN"},

    # --- General Information ---
    {"patient_id": "10004235", "input": "What is Metformin used for?", "category": "General Info - Purpose", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Tell me about Furosemide", "category": "General Info - About", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10000032", "input": "What class of drug is Aspirin?", "category": "General Info - Drug Class", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10001217", "input": "What type of medication is Insulin?", "category": "General Info - Type", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Why am I taking this medication?", "category": "General Info - Why", "expected_intent": "general", "expected_risk": "GREEN"},

    # --- Natural Language Variations ---
    {"patient_id": "10004235", "input": "My Metformin - what's it for?", "category": "NL Variation - Casual", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Side effects?", "category": "NL Variation - Brief", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Could you please provide information about the potential adverse effects of Metformin?", "category": "NL Variation - Formal", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Forgot meds", "category": "NL Variation - Very Brief", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},
    {"patient_id": "10000032", "input": "I need to know if there are any reasons I shouldn't be taking Aspirin", "category": "NL Variation - Long Form", "expected_intent": "contraindication", "expected_risk": "GREEN"},

    # --- Edge Cases ---
    {"patient_id": None, "input": "What are the side effects of Metformin?", "category": "Edge Case - No Patient ID", "expected_intent": "side_effect"},
    {"patient_id": "99999999", "input": "Tell me about my medications", "category": "Edge Case - Invalid Patient ID", "expected_intent": "general"},
    {"patient_id": "10004235", "input": "Medication info", "category": "Edge Case - Vague", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Can you help me?", "category": "Edge Case - Very General", "expected_intent": "general", "expected_risk": "GREEN"},

    # --- Multiple Medications ---
    {"patient_id": "10004235", "input": "Tell me about all my medications", "category": "Multiple Meds - All Info", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "What are the side effects of my medications?", "category": "Multiple Meds - All Side Effects", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "I forgot to take all my medications today", "category": "Multiple Meds - All Missed", "expected_intent": "missed_dose", "expected_risk": "ORANGE"},

    # --- Specific Concerns ---
    {"patient_id": "10004235", "input": "My Metformin makes me feel sick", "category": "Specific Concern - Nausea", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "I'm dizzy after taking Furosemide", "category": "Specific Concern - Dizziness", "expected_intent": "side_effect", "expected_risk": "GREEN"},
    {"patient_id": "10001217", "input": "My blood sugar is low after Insulin", "category": "Specific Concern - Hypoglycemia", "expected_intent": "side_effect", "expected_risk": "ORANGE"},
    {"patient_id": "10000032", "input": "Aspirin gave me heartburn", "category": "Specific Concern - Heartburn", "expected_intent": "side_effect", "expected_risk": "GREEN"},

    # --- Dosage Questions ---
    {"patient_id": "10004235", "input": "How much Metformin should I take?", "category": "Dosage - Amount", "expected_intent": "instruction", "expected_risk": "GREEN"},
    {"patient_id": "10004235", "input": "Is my dose of Furosemide correct?", "category": "Dosage - Verification", "expected_intent": "general", "expected_risk": "GREEN"},
    {"patient_id": "10001217", "input": "How many units of Insulin do I need?", "category": "Dosage - Units", "expected_intent": "instruction", "expected_risk": "GREEN"},
]


# ============================================================================
# EXECUTION & CSV GENERATION
# ============================================================================

def execute_appointment_test(test_case: Dict) -> Dict:
    """Execute a single appointment test case through workflow"""
    try:
        # Create initial state
        state: VoiceAgentState = {
            "user_input": test_case["input"],
            "patient_id": test_case.get("patient_id"),
            "intent": None,
            "parsed_data": {},
            "appointment_response": None,
            "response": None,
            "voice_enabled": False,
            "session_id": "validation_test",
            "timestamp": datetime.now().isoformat(),
            "log_entry": None,
            "followup_response": None,
            "medication_response": None,
            "caregiver_response": None,
            "help_response": None,
        }

        # Execute through workflow (routing will direct to appointment)
        result_state = voice_agent_workflow.invoke(state)

        # Parse input to get triage info
        parsed = parse_patient_input(test_case["input"], test_case.get("patient_id"))

        # Determine triage tier from parsed symptoms
        triage_tier, triage_rules = triage_category(parsed.get("symptoms", {}))

        return {
            "category": test_case.get("category", "Unknown"),
            "patient_id": test_case.get("patient_id", "N/A"),
            "user_input": test_case["input"],
            "expected_intent": test_case.get("expected_intent", "N/A"),
            "actual_intent": parsed.get("action", "unknown"),
            "expected_triage": test_case.get("expected_triage", "N/A"),
            "actual_triage": triage_tier,
            "triage_rules_matched": ", ".join(triage_rules) if triage_rules else "None",
            "policy_check": test_case.get("policy_check", "N/A"),
            "agent_response": result_state.get("response", "No response"),
            "parsed_data": json.dumps(parsed, default=str),
            "symptoms_detected": "Yes" if parsed.get("symptoms", {}).get("present") else "No",
            "severity_0_10": parsed.get("symptoms", {}).get("severity_0_10", "N/A"),
            "fever_f": parsed.get("symptoms", {}).get("fever_f", "N/A"),
            "preferred_date": parsed.get("preferred_date", "N/A"),
            "reason": parsed.get("reason", "N/A"),
        }
    except Exception as e:
        return {
            "category": test_case.get("category", "Unknown"),
            "patient_id": test_case.get("patient_id", "N/A"),
            "user_input": test_case["input"],
            "expected_intent": test_case.get("expected_intent", "N/A"),
            "actual_intent": "ERROR",
            "expected_triage": test_case.get("expected_triage", "N/A"),
            "actual_triage": "ERROR",
            "triage_rules_matched": "ERROR",
            "policy_check": test_case.get("policy_check", "N/A"),
            "agent_response": f"ERROR: {str(e)}",
            "parsed_data": "ERROR",
            "symptoms_detected": "ERROR",
            "severity_0_10": "ERROR",
            "fever_f": "ERROR",
            "preferred_date": "ERROR",
            "reason": "ERROR",
        }


def execute_medication_test(test_case: Dict) -> Dict:
    """Execute a single medication test case through workflow"""
    try:
        # Create initial state
        state: VoiceAgentState = {
            "user_input": test_case["input"],
            "patient_id": test_case.get("patient_id"),
            "intent": None,
            "parsed_data": {},
            "medication_response": None,
            "response": None,
            "voice_enabled": False,
            "session_id": "validation_test",
            "timestamp": datetime.now().isoformat(),
            "log_entry": None,
            "appointment_response": None,
            "followup_response": None,
            "caregiver_response": None,
            "help_response": None,
        }

        # Execute through workflow
        result_state = voice_agent_workflow.invoke(state)

        # Parse query to get intent
        parsed = llm_parse_query(test_case["input"])
        risk = llm_score_risk(parsed)

        return {
            "category": test_case.get("category", "Unknown"),
            "patient_id": test_case.get("patient_id", "N/A"),
            "user_input": test_case["input"],
            "expected_intent": test_case.get("expected_intent", "N/A"),
            "actual_intent": parsed.get("intent", "unknown"),
            "expected_risk": test_case.get("expected_risk", "N/A"),
            "actual_risk": risk,
            "agent_response": result_state.get("response", "No response"),
            "parsed_data": json.dumps(parsed, default=str),
            "drugs_mentioned": json.dumps(parsed.get("drugs_mentioned", []), default=str),
            "language": parsed.get("language", "en"),
        }
    except Exception as e:
        return {
            "category": test_case.get("category", "Unknown"),
            "patient_id": test_case.get("patient_id", "N/A"),
            "user_input": test_case["input"],
            "expected_intent": test_case.get("expected_intent", "N/A"),
            "actual_intent": "ERROR",
            "expected_risk": test_case.get("expected_risk", "N/A"),
            "actual_risk": "ERROR",
            "agent_response": f"ERROR: {str(e)}",
            "parsed_data": "ERROR",
            "drugs_mentioned": "ERROR",
            "language": "ERROR",
        }


def generate_appointment_validation_dataset():
    """Generate validation dataset for appointment agent"""
    print(f"\n{'='*80}")
    print("GENERATING APPOINTMENT AGENT VALIDATION DATASET")
    print(f"{'='*80}\n")

    results = []
    for i, test_case in enumerate(APPOINTMENT_TEST_CASES, 1):
        print(f"[{i}/{len(APPOINTMENT_TEST_CASES)}] Processing: {test_case['category']}")
        result = execute_appointment_test(test_case)
        results.append(result)

    # Write to CSV
    output_file = OUTPUT_DIR / "appointment_agent_validation.csv"
    fieldnames = [
        "category", "patient_id", "user_input",
        "expected_intent", "actual_intent",
        "expected_triage", "actual_triage", "triage_rules_matched",
        "policy_check", "symptoms_detected", "severity_0_10", "fever_f",
        "preferred_date", "reason",
        "agent_response", "parsed_data"
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Generated {len(results)} test cases")
    print(f"[OK] Saved to: {output_file}\n")
    return str(output_file)


def generate_medication_validation_dataset():
    """Generate validation dataset for medication agent"""
    print(f"\n{'='*80}")
    print("GENERATING MEDICATION AGENT VALIDATION DATASET")
    print(f"{'='*80}\n")

    results = []
    for i, test_case in enumerate(MEDICATION_TEST_CASES, 1):
        print(f"[{i}/{len(MEDICATION_TEST_CASES)}] Processing: {test_case['category']}")
        result = execute_medication_test(test_case)
        results.append(result)

    # Write to CSV
    output_file = OUTPUT_DIR / "medication_agent_validation.csv"
    fieldnames = [
        "category", "patient_id", "user_input",
        "expected_intent", "actual_intent",
        "expected_risk", "actual_risk",
        "agent_response", "parsed_data", "drugs_mentioned", "language"
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Generated {len(results)} test cases")
    print(f"[OK] Saved to: {output_file}\n")
    return str(output_file)


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("VOICE AGENT VALIDATION DATASET GENERATOR")
    print("="*80)
    print("\nThis script will generate comprehensive validation datasets for:")
    print(f"  1. Appointment Agent (~{len(APPOINTMENT_TEST_CASES)} test cases)")
    print(f"  2. Medication Agent (~{len(MEDICATION_TEST_CASES)} test cases)")
    print("\nEach test case will be executed through the actual agent code.")
    print("Results will be exported to CSV format for client review.")
    print("="*80 + "\n")

    print("Starting generation...\n")

    # Generate datasets
    appt_file = generate_appointment_validation_dataset()
    med_file = generate_medication_validation_dataset()

    # Summary
    print("\n" + "="*80)
    print("GENERATION COMPLETE!")
    print("="*80)
    print(f"\nValidation datasets saved to:")
    print(f"  📄 {appt_file}")
    print(f"  📄 {med_file}")
    print(f"\nYou can now review these CSV files and share with clients for validation.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
