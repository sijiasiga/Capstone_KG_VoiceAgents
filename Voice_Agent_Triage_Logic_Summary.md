# Voice Agent Triage Logic Summary
**CMU x Zyter Capstone Project | For Clinical Validation**

---

# PART 1: Appointment Agent Triage Logic

## 🔴 RED TIER - Emergency (Go to ER immediately + Alert nurse)

| Symptom Category | Triggers | Example Patient Inputs |
|-----------------|----------|----------------------|
| **Chest Pain** | chest pain, chest tightness, pressure in chest | "I have chest pain and need an appointment" |
| **Shortness of Breath** | shortness of breath, trouble breathing, can't breathe | "I'm having trouble breathing" |
| **High Fever** | Temperature ≥ 101.5°F | "I have a fever of 102" |
| **Severe Pain** | Pain severity ≥ 8/10 | "I'm in severe pain, level 9 out of 10" |
| **Neurological Deficits** | numbness, weakness, slurred speech, vision changes | "I have numbness in my arm" |
| **Syncope** | fainted, passed out, lost consciousness | "I fainted earlier today" |
| **Wound Dehiscence** | incision opening, pus, yellow/green drainage | "My incision is opening up" |

**Action:**
- Direct patient to emergency department immediately
- Suggest calling 911 if needed
- Alert on-call nurse automatically
- Log incident for provider review

---

## 🟠 ORANGE TIER - Urgent (Nurse callback within 24hrs + Tentative appointment hold)

| Symptom Category | Triggers | Example Patient Inputs |
|-----------------|----------|----------------------|
| **Moderate Pain** | Pain severity 5-7/10 | "I have pain around 6 out of 10" |
| **Low-Grade Fever** | Temperature 99.5 - 101.4°F | "I have a fever of 100 degrees" |
| **Dizziness** | dizzy, lightheaded, vertigo | "I've been feeling dizzy" |
| **Wound Concerns** | redness around wound, mild swelling | "My wound has some redness around it" |
| **Post-Op Issues** | Within 30 days of surgery + any symptom | "It's been 2 weeks since surgery, slight pain" |

**Action:**
- Schedule nurse callback same day
- Place tentative appointment hold (24-48 hours)
- Log symptoms for provider review
- Monitor for escalation

---

## 🟢 GREEN TIER - Routine (Log for provider review at next visit)

| Scenario | Example Patient Inputs |
|----------|----------------------|
| **Mild Symptoms** | Pain < 5/10, minor discomfort | "I have a slight headache" |
| **No Symptoms Mentioned** | Administrative requests only | "I want to reschedule my appointment" |
| **General Check-ins** | Status inquiries | "What's my appointment?" |

**Action:**
- Log symptom report in patient record
- Proceed with requested appointment action (schedule/reschedule/cancel)
- No immediate clinical intervention
- Provider reviews at next scheduled visit

---

## Appointment Agent Policy Rules

### 1. **Minor Consent** (Age < 18)
- **Trigger:** Patient age < 18 in database OR patient states age < 18
- **Action:** Require parental/guardian consent on file
- **Response:** "This request requires provider approval. I can submit that request for you, and the provider's office will contact you to confirm."

### 2. **Referral/Authorization Required**
- **Trigger:** Appointment type = "Surgery" OR "Consultation" OR plan requires referral
- **Action:** Submit request for provider approval
- **Response:** "This request requires provider approval. I can submit that request for you, and the provider's office will contact you to confirm."

### 3. **Surgery <48 Hours Rule**
- **Trigger:** Surgery appointment scheduled within next 48 hours
- **Action:** Require provider approval for any changes
- **Response:** "This request requires provider approval. I can submit that request for you, and the provider's office will contact you to confirm."

### 4. **Telehealth Eligibility**
- **RED tier:** Never eligible for telehealth (requires in-person)
- **ORANGE tier:** Case-by-case (e.g., cardiology follow-up OK, wound check not OK)
- **GREEN tier:** Eligible for telehealth if appointment type supports it

### 5. **Post-Op Monitoring (30-Day Window)**
- **Trigger:** Patient had surgery within past 30 days
- **Action:** Enhanced symptom monitoring, prioritize surgical team appointments
- **Note:** Any symptom reported within 30 days of surgery escalates to at least ORANGE

---

# PART 2: Medication Agent Risk Assessment Logic

## Query Types Handled

| Query Type | What Patient Asks | Example |
|-----------|------------------|---------|
| **Side Effects** | What side effects to expect | "What are the side effects of Metformin?" |
| **Missed Dose** | What to do if dose forgotten | "I forgot to take my Metformin this morning" |
| **Double Dose** | Accidentally took extra dose | "I took my medication twice by mistake" |
| **Drug Interactions** | Can I take X with Y? | "Can I take Metformin with alcohol?" |
| **Instructions** | How/when to take medication | "Should I take Metformin with food?" |
| **Contraindications** | Is this drug safe for my condition? | "Can I take this with kidney problems?" |
| **General Info** | What is this drug for? | "What is Metformin used for?" |

---

## 🔴 RED TIER - Urgent Medical Care Needed

| Scenario | Triggers | Example Patient Inputs |
|----------|----------|----------------------|
| **Double Dose - High Risk Drugs** | Took 2x dose of: Insulin, Warfarin, high-dose diuretics, opioids | "I accidentally took two doses of Insulin" |
| **Dangerous Interactions** | High-risk combinations mentioned | "Can I take warfarin with ibuprofen?" |
| **Serious Contraindication** | Medication contraindicated for patient's condition | "Can I take Aspirin? I have a bleeding disorder" |
| **Severe Symptom After Dose** | Life-threatening side effect reported | "I'm having trouble breathing after taking my medication" |

**Action:**
- Instruct patient to seek immediate medical care
- Contact poison control if overdose
- Alert healthcare provider
- Log incident for follow-up

**Response Example:**
> "[HIGH RISK] Please seek immediate medical care. If you took a double dose, contact poison control at 1-800-222-1222 or go to the nearest emergency department."

---

## 🟠 ORANGE TIER - Nurse Callback Recommended

| Scenario | Triggers | Example Patient Inputs |
|----------|----------|----------------------|
| **Missed Dose - Time-Sensitive Drugs** | Missed Insulin, anticoagulants, heart medications | "I didn't take my Insulin this morning" |
| **Moderate Interactions** | Potential interaction but not immediately dangerous | "Can I take Metformin with alcohol?" |
| **Bothersome Side Effects** | Non-emergency side effects affecting quality of life | "I've been feeling nauseous after taking Metformin" |
| **Double Dose - Lower Risk Drugs** | Took 2x dose of common meds (e.g., Metformin, statins) | "I think I took my Metformin twice today" |

**Action:**
- Have nurse call patient same day
- Provide interim guidance if available
- Monitor situation
- Log for provider review

**Response Example:**
> "I've noted your concern about [medication]. A nurse will call you today to review this and provide guidance. In the meantime, [interim guidance if safe to provide]."

---

## 🟢 GREEN TIER - Informational / Routine Guidance

| Scenario | Triggers | Example Patient Inputs |
|----------|----------|----------------------|
| **General Side Effects Info** | Asking about common/expected effects | "What are the side effects of Metformin?" |
| **Dosing Instructions** | How/when to take medication | "Should I take this with food?" |
| **Missed Dose - Non-Critical** | Missed dose of routine medications | "I forgot my daily vitamin" |
| **General Drug Info** | Educational questions | "What is Metformin used for?" |
| **Routine Contraindication Check** | Safe contraindication inquiry | "Is Insulin safe during pregnancy?" (YES) |

**Action:**
- Provide information directly
- Log inquiry in patient record
- No immediate clinical intervention needed
- Provider reviews at next visit

**Response Example:**
> "Metformin: Common side effects include nausea, diarrhea, bloating. These often improve after a few weeks. Take with food to reduce stomach upset."

---

## Medication-Specific Risk Tiers

### High-Risk Medications (Double dose = RED)
- **Insulin** - Risk of hypoglycemia
- **Warfarin** - Risk of bleeding
- **Opioids** - Risk of respiratory depression
- **Digoxin** - Narrow therapeutic window

### Moderate-Risk Medications (Double dose = ORANGE)
- **Metformin** - Risk of lactic acidosis (rare)
- **Furosemide** - Risk of dehydration/electrolyte imbalance
- **Blood pressure medications** - Risk of hypotension

### Lower-Risk Medications (Double dose = ORANGE with guidance)
- **Aspirin** - Monitor for stomach upset
- **Statins** - Monitor for muscle pain
- **Common antibiotics** - Monitor for GI upset

---

## Drug Interaction Risk Assessment

### RED - Dangerous Combinations
- Warfarin + Ibuprofen/NSAIDs (bleeding risk)
- Metformin + Excessive alcohol (lactic acidosis)
- Multiple blood thinners together
- MAOIs + SSRIs (serotonin syndrome)

### ORANGE - Concerning Combinations
- Diuretics + NSAIDs (kidney function)
- Metformin + Moderate alcohol
- Multiple sedatives (additive effect)

### GREEN - Safe Combinations
- Patient's prescribed medications (already vetted by provider)
- Standard food/medication pairings per label

---

# PART 3: Validation Dataset Overview

## What We're Testing

### Appointment Agent Dataset (64 test cases)

**📊 [View Dataset](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/VoiceAgents/VoiceAgents_langgraph/validation_datasets/appointment_agent_validation.csv)**

| Category | # Cases | Purpose |
|----------|---------|---------|
| **Check Status** | 5 | Verify routine appointment lookup works |
| **Reschedule - Normal** | 4 | Test administrative rescheduling (GREEN) |
| **Cancel** | 3 | Test cancellation requests |
| **Schedule New** | 2 | Test new appointment booking |
| **RED Triage** | 18 | Test emergency symptom detection |
| **ORANGE Triage** | 8 | Test urgent symptom detection |
| **Policy Checks** | 8 | Test minor consent, referral rules, telehealth, surgery timing |
| **NL Variations** | 6 | Test casual/formal/brief language |
| **Edge Cases** | 4 | Test missing patient ID, invalid ID, greetings |
| **Multiple Concerns** | 2 | Test combined administrative + symptom requests |

### Medication Agent Dataset (58 test cases)

**📊 [View Dataset](https://github.com/sijiasiga/Capstone_KG_VoiceAgents/blob/main/VoiceAgents/VoiceAgents_langgraph/validation_datasets/medication_agent_validation.csv)**

| Category | # Cases | Purpose |
|----------|---------|---------|
| **Side Effects** | 8 | Test side effect info retrieval |
| **Missed Dose** | 6 | Test missed dose guidance and risk assessment |
| **Double Dose** | 5 | Test overdose detection and RED flagging |
| **Drug Interactions** | 5 | Test interaction warnings (including alcohol) |
| **Instructions** | 6 | Test dosing/timing/food guidance |
| **Contraindications** | 5 | Test safety checks for pregnancy, kidney, liver issues |
| **General Info** | 5 | Test medication education queries |
| **NL Variations** | 5 | Test different phrasing styles |
| **Edge Cases** | 4 | Test missing patient ID, vague queries |
| **Multiple Meds** | 3 | Test handling of multiple medications at once |
| **Specific Concerns** | 4 | Test symptom reporting after taking medication |
| **Dosage** | 3 | Test dosage verification queries |

---

## Key Discrepancies We Found

### Appointment Agent Issues
1. **Line 19:** "Tightness in my chest" → Expected RED, got GREEN ❌
2. **Line 34:** "I fainted earlier today" → Expected RED, got GREEN ❌
3. **Line 44:** Wound swelling → Expected ORANGE, got RED (over-escalation)
4. **Line 50:** Telehealth request → Intent misclassified as "general" instead of "reschedule"

### Medication Agent Issues
1. **Missed dose risk inconsistency** - Some missed Insulin doses got RED, others GREEN
2. **Double dose responses** - Not all double doses trigger RED flag appropriately
3. **Pregnancy contraindications** - Insulin flagged as RED when it should be GREEN (safe in pregnancy)
4. **Intent classification** - Some queries misclassified (e.g., "what should I watch out for" as instruction vs side_effect)

---

# Questions for Clinical Validation

## Appointment Agent

1. **Are RED flag thresholds appropriate?**
   - Fever ≥ 101.5°F = RED (or should it be 100.4°F / 103°F?)
   - Pain ≥ 8/10 = RED (or should it be 7/10 / 9/10?)

2. **Should all wound-related symptoms be ORANGE?**
   - When is redness/swelling GREEN vs ORANGE vs RED?

3. **Is 30-day post-op monitoring correct?**
   - Should it vary by surgery type?

4. **Missing RED flags?**
   - Should we add: severe bleeding, confusion, inability to urinate, etc.?

5. **Is "go to ER" the right default for RED?**
   - Or should providers customize (e.g., warm transfer to nurse)?

## Medication Agent

1. **Missed dose risk tiers - when is it GREEN vs ORANGE vs RED?**
   - Is missed Insulin always ORANGE/RED?
   - Are missed vitamins/statins GREEN?

2. **Should ALL double doses be RED?**
   - Or can some be ORANGE with monitoring?

3. **Pregnancy contraindications - please validate our list**
   - Insulin = GREEN (safe)
   - Aspirin = ORANGE/RED (depends on trimester)
   - ACE inhibitors = RED (teratogenic)

4. **Drug interaction severity - are our ORANGE/RED classifications correct?**
   - Metformin + alcohol = ORANGE or RED?
   - Warfarin + ibuprofen = RED?

---

**Document Version:** 1.0
**Last Updated:** November 11, 2025
**Contact:** Christine Ma (xm3@andrew.cmu.edu)
