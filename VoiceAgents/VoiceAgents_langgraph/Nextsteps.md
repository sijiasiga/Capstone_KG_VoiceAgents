# VoiceAgents LangGraph – Remaining Work

##  Data Extension and Policy Refinement

**Status:** IN PROGRESS

**Goal**
Expand synthetic datasets, refine policies and prompts, and improve evaluation metrics to make comprehensive testing and evaluation plausible.

**Description**
To achieve reliable evaluation and testing, we need:
1. Larger, more diverse datasets covering edge cases and varied scenarios
2. Refined policies and prompts based on evaluation results
3. Comprehensive validation datasets that test system behavior across different conditions
4. Clear documentation of data governance and synthetic data policies

This ongoing work ensures the system handles real-world scenarios effectively and can be properly evaluated.

**Implementation**

### Expand Core Data Files

**Patients Dataset (`data/patients.csv`):**
- Add more diverse patient profiles (different ages, conditions, demographics)
- Include patients with multiple chronic conditions
- Add edge cases: patients with no appointments, patients with many appointments
- Ensure realistic distribution of patient IDs and demographic data

**Appointments Dataset (`data/appointments.csv`):**
- Expand appointment types (follow-up, surgery, consultation, emergency)
- Add various appointment statuses (scheduled, confirmed, cancelled, completed)
- Include appointments with different time ranges (same-day, next week, months out)
- Add edge cases: overlapping appointments, rescheduled appointments, missed appointments

**Prescriptions Dataset (`data/prescriptions.csv`):**
- Add more medication combinations (multiple medications per patient)
- Include various medication types (chronic, acute, as-needed)
- Add edge cases: discontinued medications, dosage changes, medication interactions
- Ensure realistic drug names and prescribing patterns

**Caregivers Dataset (`data/caregivers.csv`):**
- Add more caregiver-patient relationships
- Include various consent statuses
- Add edge cases: multiple caregivers per patient, revoked consent

### Expand Validation Datasets

**Current Validation Datasets:**
- `validation_datasets/appointment_agent_validation.csv`
- `validation_datasets/medication_agent_validation.csv`

**Additional Validation Datasets to Create:**

1. **`validation_datasets/followup_agent_validation.csv`**
   - Test cases for symptom reporting across all triage tiers (RED/ORANGE/GREEN)
   - Edge cases: ambiguous symptoms, multiple symptoms, severity variations
   - Test triage classification accuracy

2. **`validation_datasets/caregiver_agent_validation.csv`**
   - Test cases for caregiver summary generation
   - Edge cases: no symptom data, no medication data, partial data
   - Test consent validation and access control

3. **`validation_datasets/routing_agent_validation.csv`**
   - Test cases for intent classification and routing
   - Edge cases: ambiguous intents, multiple intents, patient ID extraction from various formats
   - Test routing accuracy

4. **`validation_datasets/end_to_end_validation.csv`**
   - Complete conversation flows from start to finish
   - Multi-turn interactions
   - Complex scenarios combining multiple agent types

### Refine Policies and Prompts

**Based on Evaluation Results:**

1. **Review Policy Files (`policy/agents/*.json`):**
   - Analyze evaluation results to identify policy gaps
   - Refine escalation rules based on false positives/negatives
   - Update scope and restrictions based on observed behavior
   - Document policy changes with rationale

2. **Refine Global System Prompt (`policy/system_behavior.py`):**
   - Adjust safety language based on evaluation feedback
   - Clarify non-clinical boundaries
   - Improve triage guidance
   - Test prompt variations for better performance

3. **Update Safety Rules (`policy/safety_rules.json`):**
   - Refine RED/ORANGE/GREEN flag definitions based on evaluation
   - Add edge cases discovered during testing
   - Clarify escalation paths
   - Ensure rules are comprehensive and accurate

### 8.4 Improve Evaluation Metrics

**Evaluation Scripts (`evaluation/`):**
- Expand test dataset (`evaluation/test_dataset.json`) with more scenarios
- Add metrics for:
  - Intent classification accuracy
  - Triage classification accuracy (RED/ORANGE/GREEN)
  - Patient ID extraction accuracy
  - Response quality metrics
  - Edge case handling
- Generate confusion matrices for all classification tasks
- Add performance benchmarks (response time, token usage)

**Continuous Evaluation:**
- Run evaluation after each policy/prompt change
- Track metrics over time
- Identify regression issues early
- Document improvements in evaluation results

### Data Governance Documentation

**Create `docs/data_policy.md`:**
- Document that all datasets are synthetic and non-identifiable
- Explain data generation rules and validation criteria
- Define data governance policies:
  - How to generate new synthetic data
  - How to validate data quality
  - How to maintain data consistency
  - How to update datasets without breaking compatibility
- Provide examples of synthetic data generation
- Document data schemas and expected formats

**Data Quality Assurance:**
- Ensure all CSV files parse correctly with `database.py`
- Validate data consistency (e.g., patient IDs match across files)
- Check for missing required fields
- Verify data types and formats

### Testing Infrastructure

**Expand Test Suite (`tests/test_agents.py`):**
- Add tests for edge cases discovered during evaluation
- Add tests for policy compliance
- Add tests for data validation
- Add performance tests
- Add integration tests for complex workflows

**Test Coverage:**
- Ensure all agent types have test coverage
- Test all triage tiers (RED/ORANGE/GREEN)
- Test routing accuracy
- Test error handling and fallbacks
- Test data access patterns

**Verification**

After completing:

* No parsing or path errors when loading data
* CLI runs normally with expanded datasets
* Evaluation metrics show improved accuracy and coverage
* All validation datasets are comprehensive and test realistic scenarios
* Policies and prompts are refined based on evaluation results
* Data governance documentation is complete and clear
* Test suite demonstrates system reliability across diverse scenarios
* System handles edge cases gracefully
* Reviewers can confirm data policy compliance

**Success Criteria:**

1. **Dataset Quality:**
   - At least 100+ patients with diverse profiles
   - 200+ appointments covering various scenarios
   - 150+ prescriptions with realistic medication patterns
   - Comprehensive validation datasets for all agents

2. **Evaluation Metrics:**
   - Intent classification accuracy > 90%
   - Triage classification accuracy > 95% (especially RED flags)
   - Patient ID extraction accuracy > 95%
   - All edge cases handled correctly

3. **Policy Refinement:**
   - Policies updated based on evaluation feedback
   - Prompts refined for better performance
   - Safety rules comprehensive and accurate
   - Documentation complete

4. **Testing:**
   - Test coverage for all agent types
   - Tests pass consistently
   - Edge cases handled
   - Performance acceptable

**Ongoing Work:**

This part is iterative and ongoing. As the system is evaluated and tested, continue to:
- Expand datasets with new scenarios discovered during evaluation
- Refine policies and prompts based on performance metrics
- Improve validation datasets to cover gaps
- Update documentation as policies evolve
- Enhance test coverage for new edge cases

---

## File Format Rationale

| Purpose                                  | Recommended Format                      | Reason                                        |
| ---------------------------------------- | --------------------------------------- | --------------------------------------------- |
| Runtime constants (e.g., system prompt)  | `.py`                                   | Allows import and dynamic reference           |
| Structured policies (agent rules)        | `.json`                                 | Machine-readable, editable, schema-consistent |
| Human documentation (guides, boundaries) | `.md`                                   | Readable on GitHub and Cursor                 |
| Evaluation/Test outputs                  | `.jsonl`                                | Append-only and easy to parse                 |
| Legacy business rules                    | Keep existing `data/policy_config.json` | Backward compatibility                        |
| Validation datasets                      | `.csv`                                  | Easy to review, edit, and version control     |

---

## Expected End State

After completing:

* All agents share a unified system prompt and safety policy (completed)
* Agent-specific restrictions and escalation logic are externally defined (completed)
* System handles API and audio failures gracefully (completed)
* Logging and evaluation are structured and auditable (completed)
* **Expanded datasets cover diverse scenarios and edge cases**
* **Validation datasets enable comprehensive testing and evaluation**
* **Policies and prompts are refined based on evaluation results**
* **Data governance documentation is complete**
* **Test suite demonstrates system reliability across diverse scenarios**
* The whole package remains runnable and test-verified
* System is ready for production-like evaluation and demonstration
