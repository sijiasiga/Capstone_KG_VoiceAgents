# Safety and Clinical Boundaries Documentation

## Non-Clinical Disclaimer

**This system is NOT a licensed medical provider.** The VoiceAgents system is designed for post-discharge patient triage and follow-up assistance. It is a healthcare support tool that helps patients navigate non-emergency healthcare needs, but it does not provide medical diagnosis, treatment, or prescriptions.

### What This System Does:
- Helps patients check appointment status and schedule/reschedule appointments
- Logs patient-reported symptoms for provider review
- Provides general medication information (side effects, interactions, missed dose guidance)
- Generates caregiver summaries for patients with linked caregivers
- Routes patients to appropriate care levels based on symptom severity

### What This System Does NOT Do:
- Provide medical diagnosis
- Prescribe medications or treatments
- Modify existing prescriptions
- Replace professional medical judgment
- Make treatment recommendations beyond general guidance

## Triage System Explanation

The system uses a three-tier triage classification to assess patient-reported symptoms and determine appropriate escalation:

### RED Flags (Emergency - Immediate Action Required)

**Symptoms:**
- Chest pain, chest tightness, pain in chest
- Shortness of breath, trouble breathing
- Wound complications (opening, drainage, infection signs)
- High fever (>= 101.5°F)
- Severe pain (>= 8/10 on pain scale)
- Neurological deficits (numbness, weakness, slurred speech)
- Syncope (fainting)

**System Response:**
- Directs patient to emergency department immediately
- Alerts healthcare provider automatically
- Does NOT proceed with routine appointment scheduling or symptom logging as primary action

### ORANGE Flags (Concerning - Nurse Callback Required)

**Symptoms:**
- Moderate pain (5-7/10 on pain scale)
- Low-grade fever (99.5-101.4°F)
- Dizziness
- Hyperglycemia (blood sugar > 300)
- Wound redness/swelling

**System Response:**
- Schedules nurse callback for same day
- Holds tentative appointment slot available
- Logs symptoms for provider review
- May escalate to RED if symptoms worsen

### GREEN Flags (Normal - Routine Monitoring)

**Symptoms:**
- Mild discomfort
- Routine recovery symptoms
- Non-urgent concerns

**System Response:**
- Logs symptoms for provider review at next scheduled appointment
- Provides general reassurance and self-care guidance where appropriate
- No immediate escalation required

## Escalation Paths

### Automatic Escalation Triggers:

1. **RED Flag Symptoms Detected**
   - Immediate: Direct to emergency department
   - Automatic: Provider notification sent
   - Action: System does not proceed with routine operations

2. **ORANGE Flag Symptoms Detected**
   - Immediate: Nurse callback scheduled
   - Secondary: Tentative appointment hold placed
   - Action: Routine operations can continue but are flagged

3. **Missing Consent (Minors)**
   - Appointment operations blocked until caregiver consent verified
   - Caregiver summaries require consent on file

4. **Provider Approval Required**
   - Certain appointment types (e.g., HMO plans) require provider approval
   - System cannot auto-schedule, submits request for approval

5. **Uncertainty in Assessment**
   - System defaults to escalation when uncertain
   - "If uncertain, escalate to human nurse" principle

## Agent-Specific Do's and Don'ts

### Appointment Agent

**DO:**
- Check appointment status
- Schedule/reschedule appointments within policy constraints
- Cancel appointments with confirmation
- Enforce business rules (post-op windows, telehealth eligibility)
- Verify consent for minors

**DON'T:**
- Provide diagnosis
- Modify medications
- Schedule outside approved timeframes
- Bypass consent requirements

**Escalation Triggers:**
- RED flag symptoms mentioned
- Missing caregiver consent for minors
- Provider approval required (HMO plans)
- Urgent appointment requests

### Followup Agent

**DO:**
- Log patient-reported symptoms
- Assess symptom severity
- Classify symptoms into triage tiers (RED/ORANGE/GREEN)
- Provide general reassurance for GREEN symptoms
- Schedule nurse callbacks for ORANGE symptoms

**DON'T:**
- Provide diagnosis
- Recommend specific treatments
- Modify medications
- Provide medical advice beyond general guidance

**Escalation Triggers:**
- RED flag symptoms (chest pain, severe pain, high fever, etc.)
- Severe pain (>= 8/10)
- Neurological deficits
- Any symptom that matches RED flag criteria

### Medication Agent

**DO:**
- Provide information about side effects
- Advise on missed dose scenarios
- Explain drug interactions
- Provide food guidance for medications
- List contraindications

**DON'T:**
- Prescribe new medications
- Modify dosages
- Recommend treatment changes
- Provide diagnosis based on medication questions

**Escalation Triggers:**
- Severe side effects reported
- Multiple missed doses (>= 3)
- Serious drug interactions identified
- RED risk level assessment

### Caregiver Agent

**DO:**
- Generate weekly patient summaries
- Aggregate symptom trends
- Track medication adherence
- Provide risk scoring

**DON'T:**
- Share detailed medical information
- Provide diagnostic information
- Generate summaries without consent
- Share information for patients without linked caregivers

**Escalation Triggers:**
- High risk patient status detected
- Multiple missed medications
- Worsening symptom trends
- Risk score exceeds threshold

### Help Agent

**DO:**
- Provide general conversation
- Offer system navigation help
- Answer non-medical questions
- Redirect to appropriate agents

**DON'T:**
- Provide medical advice
- Offer diagnosis
- Recommend treatments
- Answer emergency medical questions directly

**Escalation Triggers:**
- Medical emergency mentions
- RED flag symptoms mentioned
- Requests for diagnosis or treatment

## Safety Language Standards

All agent responses should include clear safety language when:
- Symptoms are mentioned (remind patient system is not a clinician)
- Medical advice might be requested (redirect to appropriate care)
- Emergency situations are detected (direct to emergency care)
- Uncertainty exists (escalate to human nurse)

### Example Safety Phrases:
- "I'm a healthcare assistant, not a licensed clinician..."
- "For medical emergencies, please go to the nearest emergency department..."
- "I've logged this for your provider to review..."
- "This requires immediate medical attention. Please seek emergency care..."

## Compliance and Data Handling

- All patient interactions are logged to `logs/` directory
- Logs include timestamps, patient IDs, user inputs, and agent responses
- Triage classifications are recorded for auditability
- No PHI (Protected Health Information) is stored beyond what's necessary for operation
- All data used is synthetic and non-identifiable (see `docs/data_policy.md`)

## Revision History

- **Initial Version**: Establishes baseline safety boundaries and triage system
- **Last Updated**: See `Updates.md` for latest changes

## Contact and Support

For questions about safety boundaries or clinical compliance:
- Review agent-specific policies in `policy/agents/`
- Check global system behavior in `policy/system_behavior.py`
- Refer to `README.md` for system overview

---

**Remember**: When in doubt, escalate. This system prioritizes patient safety over convenience.

