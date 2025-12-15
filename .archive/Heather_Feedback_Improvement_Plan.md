# Improvement Plan Based on Heather's Clinical Validation Feedback
**Date:** November 2025
**Total Comments:** 31 (18 medication + 13 appointment)

---

## Executive Summary

Heather's feedback highlights a critical theme: **Add probing questions before escalation**. The current system auto-escalates based on keyword detection, but clinical triage requires context gathering first.

**Key Insight:** "Phase 1" is good for keyword detection, but "Phase 2" needs conversational probing to make nuanced clinical decisions.

---

## PRIORITY 1: Critical Fixes (Must Do Before Final Demo)

### 1. **Fix Medication Agent - Only Discuss Requested Medication**
**Issue:** Agent mentions all patient medications when asked about one specific drug (causes confusion)

**Examples from Heather's Comments:**
- Row 14: Asked about Metformin side effects → Got Furosemide info too
- Row 43: General comment - "ensure AI agents only discuss the medication the user is asking about"

**Implementation:**
```python
# BEFORE (WRONG):
def get_side_effects(patient_id):
    all_meds = database.get_prescriptions(patient_id)
    return side_effects_for_all(all_meds)  # Returns ALL meds

# AFTER (CORRECT):
def get_side_effects(patient_id, drug_name):
    # Only return info for the specific drug asked about
    drug_info = get_drug_knowledge(drug_name)
    return f"{drug_name}: {drug_info['side_effects']}"
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/medication.py` - Filter responses to only mention requested drug
- Update all medication response templates

---

### 2. **Fix Missed RED Flag Detection - Chest Tightness**
**Issue:** Row 19 - "Tightness in my chest" was classified as GREEN instead of RED

**Implementation:**
```python
# Add missing patterns to RED flag detection
RED_FLAG_PATTERNS = {
    "chest_pain": [
        "chest pain",
        "pain in chest",
        "chest tightness",  # MISSING - ADD THIS
        "tightness in chest",  # MISSING - ADD THIS
        "pressure in chest",
        "chest pressure"
    ],
    # ... rest of patterns
}
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/appointment.py` - Add missing chest pain patterns
- `policy/safety_rules.json` - Update RED flag keyword list

---

### 3. **Fix Incorrect/Non-Responsive Answers**
**Issue:** Many cases where agent didn't answer the actual question asked

**Examples:**
- Row 15 (Med): "I accidentally took two doses" → Got "Metformin is used for Diabetes" (not helpful)
- Row 20 (Med): "Can I take Metformin with Furosemide?" → Didn't answer the interaction question
- Row 46 (Med): "What are side effects of Metformin?" (no patient ID) → Should still answer generally, not refuse

**Implementation:**
- Review intent classification logic - ensure questions map to correct intents
- For general drug info questions, allow responses even without patient ID
- Ensure response templates directly answer the question asked

**Files to Update:**
- `VoiceAgents_langgraph/nodes/routing.py` - Improve intent classification
- `VoiceAgents_langgraph/nodes/medication.py` - Fix response logic for each intent

---

### 4. **Hypoglycemia = Immediate Urgency**
**Issue:** Row 55 - "My blood sugar is low after Insulin" → "Nurse will call you today" is TOO SLOW

**Heather's Comment:** "This should be escalated quickly so a direct transfer to the RN. Otherwise probe how low it is. If critically low, direct to call 911. A delay could be very serious."

**Implementation:**
```python
def handle_hypoglycemia_report(patient_input, blood_sugar=None):
    """Special handling for low blood sugar - time-sensitive emergency"""

    # If blood sugar mentioned
    if blood_sugar:
        if blood_sugar < 54:  # Critically low
            return "RED", "Your blood sugar is critically low. Please call 911 or go to the ER immediately. If you're able, drink juice or eat glucose tablets while waiting."
        elif blood_sugar < 70:  # Low but manageable
            return "ORANGE", "Your blood sugar is low. Eat 15g of fast-acting carbs (juice, glucose tablets). I'm transferring you to a nurse NOW for guidance."
    else:
        # Ask probing question first
        return "PROBE", "How low is your blood sugar? Can you check it now? Do you have a glucose meter?"

# Add to RED flag category
MEDICATION_RED_FLAGS = {
    "hypoglycemia": ["low blood sugar", "blood sugar is low", "hypoglycemic", "shaky", "dizzy after insulin"]
}
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/medication.py` - Add hypoglycemia-specific handling
- Create immediate escalation pathway (not same-day callback)

---

## PRIORITY 2: Important Improvements (Should Do)

### 5. **Add Probing Questions for RED Flags (Before ER Referral)**

**Heather's Key Feedback:** "These probably need additional probing in order to determine if it is appropriate to send to the ER."

#### **A. High Fever Probing**
**Current:** Fever ≥101.5°F → Automatic ER referral
**Needed:** Ask context first

```python
def probe_high_fever(temperature, patient_input):
    """Multi-turn conversation for fever context"""

    questions = [
        "Do you have any flu-like symptoms (body aches, cough, runny nose)?",
        "When did the fever start?",
        "Have you taken any fever-reducing medication like Tylenol or Advil?"
    ]

    # Based on answers:
    # - Flu symptoms + high fever → Nurse callback (not ER)
    # - High fever + no flu + sudden onset → ER
    # - Post-op + high fever → ER (infection risk)
```

**Heather's Example:** "If a patient has a flu and a fever >101.5 that would be expected and not an emergency."

#### **B. Severe Pain Probing**
**Current:** Pain ≥8/10 → Automatic ER referral
**Needed:** Ask type, location, onset

```python
def probe_severe_pain(severity_score):
    """Gather pain context before escalation"""

    questions = [
        "What type of pain is it? (sharp, dull, burning, throbbing)",
        "Where exactly is the pain located?",
        "Is this a new pain, or has it been ongoing?",
        "Did anything trigger it, or did it start suddenly?"
    ]

    # Based on answers:
    # - New sharp chest pain → ER
    # - Chronic pain flare-up → Nurse callback + pain management
    # - Post-op surgical site pain → Surgeon office visit
```

**Heather's Comment (Row 26):** "Will the AI agent try to scope out the type of pain the patient is having? This one might also be appropriate to send to an on call RN to evaluate first."

#### **C. Wound Issue Probing**
**Current:** Pus/drainage/opening → Automatic ER referral
**Needed:** Ask severity first

```python
def probe_wound_concern(patient_input):
    """Assess wound severity before escalation"""

    questions = [
        "How much drainage are you seeing? (small amount, large amount, continuous)",
        "What color is the drainage? (clear, yellow, green, bloody)",
        "How much has the incision opened? (small gap, large opening, can see inside)"
    ]

    # Based on answers:
    # - Minor pus + small opening → Surgeon office visit (not ER)
    # - Heavy green drainage + large opening → ER
    # - Mild redness only → Nurse callback
```

**Heather's Comment (Row 29):** "Some surgeons might want to see the patient in office vs. them going to the ER depending on how much drainage/how large the open wound is."

---

### 6. **Add Warm Transfer to RN Option (Alternative to ER)**

**Issue:** Many RED/ORANGE cases should route to on-call nurse first, not directly to ER

**Heather's Comments:**
- Row 23: "A lot of times we might want to connect them with an on call nurse first."
- Row 42: "I'd be ok if it's a warm transfer to the RN to evaluate"
- Row 44: "This one should probably be escalated to a nurse for additional details vs. going to ER."

**Implementation:**
```python
ESCALATION_PATHWAYS = {
    "immediate_911": ["chest_pain_cardiac", "stroke_symptoms", "severe_bleeding"],
    "er_referral": ["high_fever_post_op", "severe_wound_dehiscence"],
    "warm_transfer_rn": ["moderate_pain", "dizziness", "low_fever", "mild_wound_concern"],
    "nurse_callback_today": ["orange_symptoms", "medication_concerns"],
    "routine_log": ["green_symptoms"]
}

def determine_escalation_path(triage_tier, symptom_category, context):
    """Choose appropriate escalation based on clinical context"""

    # Example logic:
    if triage_tier == "RED":
        if has_context_questions_answered(context):
            # After probing, determine pathway
            if is_life_threatening(context):
                return "immediate_911"
            elif needs_immediate_eval(context):
                return "warm_transfer_rn"  # RN decides ER vs office
            else:
                return "er_referral"
        else:
            # Need to probe first
            return "probe_for_context"
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/appointment.py` - Add warm transfer option
- `policy/system_behavior.py` - Update escalation pathway logic
- Make this **provider-customizable** (some want warm transfer, others want direct ER)

---

### 7. **Add Context Gathering for Appointment Actions**

**Issue:** Agent doesn't ask WHY for reschedule/cancel/new appointment requests

**Heather's Comments:**
- Row 7: "Will the agent check the reason for the visit in order to confirm it's appropriate to push the appointment back?"
- Row 11: "Will the agent confirm the reason for the cancellation? Will the agent try to facilitate a reschedule instead?"
- Row 47: "Would be helpful to document the reason and potentially inquire about rescheduling."

**Implementation:**
```python
def handle_reschedule_request(patient_id, appointment_info):
    """Ask for context before rescheduling"""

    # Step 1: Ask why
    reason = ask_user("I see you'd like to reschedule your {appointment_type} on {date}. May I ask why you need to reschedule?")

    # Step 2: Evaluate if reschedule is appropriate
    if is_urgent_appointment(appointment_info) or is_within_48hrs(appointment_info):
        return "This appointment is marked as urgent. Let me connect you with the scheduling team to find the best option."

    # Step 3: Offer alternatives
    if reason_suggests_cancellation(reason):
        return "Would you like to cancel entirely, or would you prefer to reschedule for a later date?"

    # Step 4: Proceed with reschedule
    return reschedule_workflow(patient_id, appointment_info, reason)

def handle_cancel_request(patient_id, appointment_info):
    """Try to facilitate reschedule instead of cancellation"""

    reason = ask_user("I can help with that. May I ask why you need to cancel?")

    # Encourage reschedule over cancel
    if not reason_is_permanent(reason):
        return "I understand. Would you like to reschedule instead of canceling? I can find you another time."

    # Document reason
    log_cancellation(patient_id, appointment_info, reason)
    return "I've canceled your appointment. If you'd like to reschedule in the future, just let me know."
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/appointment.py` - Add probing for all appointment actions
- Add reason logging to appointment logs

---

### 8. **Probing for Double Dose & Missed Dose**

**Issue:** Agent escalates without knowing which medication or context

**Heather's Comments:**
- Row 10 (Med): "This shouldn't be high risk unless the patient is having symptoms. Maybe the AI agent could ask probing questions to confirm."
- Row 12 (Med): "This shouldn't be a high alert unless the member is having symptoms. The AI agent could perhaps prompt the user to ask what their blood sugar is."
- Row 19 (Med): "The AI agent should probe for what medication they took 2 dosage of."

**Implementation:**
```python
def handle_double_dose(patient_id, user_input):
    """Multi-turn conversation for double dose"""

    # Step 1: Identify which medication
    if not medication_mentioned(user_input):
        drug_name = ask_user("Which medication did you accidentally take twice?")
    else:
        drug_name = extract_drug_name(user_input)

    # Step 2: Check risk level
    drug_risk = get_drug_risk_level(drug_name)

    if drug_risk == "HIGH":  # Insulin, Warfarin, etc.
        # Step 3: Check for symptoms
        symptoms = ask_user("Are you experiencing any symptoms right now? (dizziness, nausea, bleeding, etc.)")

        if symptoms:
            return "RED", f"Please seek immediate medical care or call poison control at 1-800-222-1222. Mention you took double dose of {drug_name} and are experiencing {symptoms}."
        else:
            return "ORANGE", f"Monitor closely for symptoms. I'm connecting you with a nurse now to discuss {drug_name} double dose."

    elif drug_risk == "MODERATE":
        return "ORANGE", f"Taking a double dose of {drug_name} can cause side effects. A nurse will call you today to provide guidance on what to watch for."

    else:  # Low risk
        return "GREEN", f"A single extra dose of {drug_name} is usually not dangerous, but avoid taking your next scheduled dose. Monitor for [common side effects]."

def handle_missed_dose(patient_id, user_input):
    """Context-aware missed dose handling"""

    # Identify medication
    drug_name = extract_or_ask_drug_name(user_input)

    # Time-sensitive medications get special handling
    if drug_name.lower() == "insulin":
        blood_sugar = ask_user("What is your current blood sugar level?")
        return handle_missed_insulin(blood_sugar)

    elif is_time_critical(drug_name):  # Anticoagulants, heart meds
        return "ORANGE", f"Since {drug_name} is time-sensitive, a nurse will call you today to provide guidance."

    else:
        return "GREEN", get_missed_dose_guidance(drug_name)
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/medication.py` - Add multi-turn probing
- Create risk classification for all medications in drug_knowledge.csv

---

### 9. **Check Historical Context for Recurring Symptoms**

**Issue:** Agent logs routine visit when patient has multiple unreported symptoms

**Heather's Comment (Row 38):** "Would the agent follow up to see if the patient had already seen the provider for the other concerns? If not, this should be escalated vs. scheduling a routine visit."

**Example:** Patient reports fever 100°F (ORANGE), but system shows they reported "severe pain, chest tightness, shortness of breath" earlier this week that were never addressed.

**Implementation:**
```python
def check_symptom_history(patient_id, current_symptom):
    """Review recent symptom logs before triaging"""

    recent_symptoms = get_symptom_logs(patient_id, days=7)
    unresolved_red_flags = [s for s in recent_symptoms if s['triage'] == 'RED' and not s['resolved']]

    if unresolved_red_flags:
        return f"I see you reported {list_symptoms(unresolved_red_flags)} earlier this week. Did you see a provider for those concerns?"

        # If no:
        # "Those symptoms combined with your current {current_symptom} are concerning. Let me connect you with a nurse right away."
```

**Files to Update:**
- `VoiceAgents_langgraph/nodes/followup.py` - Add historical context check
- Query symptom_logs.csv before triaging new symptoms

---

## PRIORITY 3: Nice-to-Have Enhancements (Future Work)

### 10. **Provider-Specific Customization**
- Row 7: "It will likely vary by provider whether they'll be able to reschedule with a different provider."
- Row 14: Some providers want 2-week urgency, others don't

**Implementation:** Expand `policy_config.json` to include provider-level settings

---

### 11. **More Sophisticated Dizziness Probing**
**Heather's Comment (Row 42):** "Dizziness can be a sign of something serious (stroke, heart attack, etc.) and we'd want to direct them to ER if it was accompanied by other concerning symptoms."

**Implementation:**
```python
DIZZINESS_PROBING = [
    "Are you experiencing any of these with the dizziness: chest pain, shortness of breath, weakness, slurred speech, vision changes?",
    "Did the dizziness come on suddenly or gradually?",
    "Have you fallen or nearly fallen?"
]

# If accompanied by stroke/cardiac symptoms → ER
# If isolated dizziness → Warm transfer to RN
```

---

## Implementation Roadmap

### Week 1: Critical Fixes
- [ ] Fix medication agent to only discuss requested drug
- [ ] Add missing chest tightness patterns to RED flags
- [ ] Fix incorrect/non-responsive answers (intent classification)
- [ ] Implement hypoglycemia immediate urgency handling

### Week 2: Probing Questions
- [ ] Add high fever probing (flu symptoms, onset, duration)
- [ ] Add severe pain probing (type, location, new vs chronic)
- [ ] Add wound concern probing (severity, drainage amount/color)
- [ ] Add double dose probing (which med, symptoms)
- [ ] Add missed dose probing (which med, time-sensitive check)

### Week 3: Workflow Improvements
- [ ] Implement warm transfer to RN pathway
- [ ] Add appointment action context gathering (why reschedule/cancel)
- [ ] Add historical symptom context check
- [ ] Update escalation pathway decision logic

### Week 4: Testing & Validation
- [ ] Re-run all 122 validation test cases
- [ ] Generate updated results with Heather's scenarios
- [ ] Document changes made based on feedback
- [ ] Send updated validation to Heather for review

---

## Files Requiring Updates

### Critical Files:
1. `VoiceAgents_langgraph/nodes/medication.py` - Most medication improvements
2. `VoiceAgents_langgraph/nodes/appointment.py` - Probing questions, warm transfer
3. `VoiceAgents_langgraph/nodes/routing.py` - Fix intent classification
4. `VoiceAgents_langgraph/state.py` - May need to expand state for multi-turn conversations
5. `policy/safety_rules.json` - Update RED/ORANGE/GREEN criteria
6. `data/drug_knowledge.csv` - Add risk levels for all medications

### Supporting Files:
7. `VoiceAgents_langgraph/workflow.py` - May need conditional edges for probing
8. `policy/system_behavior.py` - Update escalation pathways
9. `VoiceAgents_langgraph/database.py` - Add symptom history queries

---

## Success Metrics

After implementing improvements, the system should:
1. ✅ Ask probing questions before RED escalations (fever, pain, wounds)
2. ✅ Only discuss the medication the user asked about
3. ✅ Properly detect all RED flag patterns (including "chest tightness")
4. ✅ Immediately escalate hypoglycemia (not same-day callback)
5. ✅ Offer warm transfer to RN as middle-ground option
6. ✅ Gather context for all appointment actions (reschedule/cancel reasons)
7. ✅ Correctly answer all user questions (no more "didn't answer the question")
8. ✅ Check symptom history before triaging as routine

---

**Next Steps:**
1. Review this plan with team
2. Prioritize which fixes to implement before final demo
3. Begin implementation starting with Priority 1 critical fixes
4. Test changes against Heather's commented validation datasets
5. Send updated system to Heather for re-validation
