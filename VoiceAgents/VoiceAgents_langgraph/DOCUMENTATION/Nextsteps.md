# VoiceAgents LangGraph – Remaining Work Overview

## 1. Data Expansion and Policy Refinement

**Status:** In Progress
**Goal:**
Enhance synthetic datasets, refine policies and prompts, and strengthen evaluation metrics for more realistic, comprehensive testing.

### Objectives

1. Enrich datasets with diverse, realistic, and edge-case scenarios.
2. Improve policies, prompts, and safety rules based on evaluation feedback.
3. Build validation datasets that fully test agent behaviors.
4. Document data governance and generation procedures.

---

## 2. Dataset Expansion

### Core Data Files

**Patients (`data/patients.csv`)**

* Add diverse demographics, chronic conditions, and edge cases (no appointments, multiple conditions).

**Appointments (`data/appointments.csv`)**

* Include varied types (consultation, surgery, emergency) and statuses (scheduled, completed, cancelled).
* Add time-based edge cases such as overlapping or rescheduled visits.

**Prescriptions (`data/prescriptions.csv`)**

* Add multi-drug cases, discontinued or adjusted medications, and realistic naming patterns.

**Caregivers (`data/caregivers.csv`)**

* Add multiple caregiver relationships and consent variations, including revoked access.

---

## 3. Validation Dataset Expansion

**To Add:**

1. **Follow-Up Agent Validation** — Test triage accuracy (RED/ORANGE/GREEN) with symptom variations.
2. **Caregiver Agent Validation** — Check summary generation and consent validation.
3. **Routing Agent Validation** — Verify intent recognition and ID extraction accuracy.
4. **End-to-End Validation** — Simulate multi-turn, multi-agent conversations.

---

## 4. Policy and Prompt Refinement

* Review and update all agent-specific policy files (`policy/agents/*.json`).
* Refine the **global system prompt** to clarify safety and non-clinical boundaries.
* Update `safety_rules.json` to improve triage definitions and escalation logic.
* Document rationale for each policy adjustment.

---

## 5. Evaluation and Metrics

**Enhancements:**

* Expand `evaluation/test_dataset.json` with diverse scenarios.
* Add metrics for:

  * Intent and triage classification accuracy
  * Patient ID extraction
  * Response quality and latency
* Generate confusion matrices and track regressions.

**Continuous Evaluation:**

* Run automated evaluations after every policy or prompt update.
* Track metric trends and document improvements.

---

## 6. Data Governance

**New File:** `docs/data_policy.md`

* Clarify that all data is synthetic and anonymized.
* Define generation and validation rules.
* Describe data quality checks, schema expectations, and update procedures.

**Quality Assurance:**

* Validate CSV formats and referential integrity across datasets.
* Ensure no missing or mismatched IDs.
* Maintain consistent types and schemas.

---

## 7. Testing and Verification

**Testing Scope:**

* Extend `tests/test_agents.py` with edge cases, policy compliance, and data validation tests.
* Include performance and integration tests across agents.

**Success Verification:**

* All data loads without parsing errors.
* CLI and evaluation scripts run successfully.
* Metrics exceed target thresholds (e.g., triage >95%).
* All tests pass with full coverage.

---

## 8. Success Criteria

| Category            | Target                                                  |
| ------------------- | ------------------------------------------------------- |
| **Dataset Quality** | ≥100 patients, ≥200 appointments, ≥150 prescriptions    |
| **Accuracy**        | Intent >90%, Triage >95%, Patient ID >95%               |
| **Policy & Safety** | All refined, documented, and validated                  |
| **Testing**         | All agents covered, edge cases pass, performance stable |

---

## 9. Ongoing Work

Continuous improvement cycle:

* Expand data as new edge cases emerge.
* Refine prompts and policies with new evaluations.
* Update documentation and validation datasets.
* Strengthen test coverage for reliability and safety.

---

## 10. File Format Rationale

| Purpose             | Format   | Reason                              |
| ------------------- | -------- | ----------------------------------- |
| Runtime constants   | `.py`    | Easy import and reference           |
| Agent policies      | `.json`  | Structured and machine-readable     |
| Documentation       | `.md`    | Human-readable and version-friendly |
| Evaluation outputs  | `.jsonl` | Append-only and parseable           |
| Validation datasets | `.csv`   | Simple review and control           |

---

**End State:**
All agents share unified safety policies, refined prompts, and validated datasets.
The system handles failures gracefully, produces auditable logs, and achieves high accuracy in testing — ready for production-style evaluation.

