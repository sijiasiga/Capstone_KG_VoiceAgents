# Test Suite Documentation

## Overview

The test suite in `test_agents.py` provides **regression testing** for the VoiceAgents LangGraph system. All tests are designed to work with or without LLM access, using rule-based fallbacks when LLMs are unavailable.

## Why Tests Are Important

1. **Regression Prevention**: Ensures that code changes don't break existing functionality
2. **Workflow Verification**: Confirms the LangGraph workflow completes without crashing
3. **Routing Logic**: Verifies intent classification and routing works correctly
4. **Fallback Resilience**: Tests that rule-based fallbacks work when LLMs fail
5. **Triage System**: Validates RED flag detection and escalation

## Running Tests

```bash
# From VoiceAgents_langgraph/ directory
pytest tests/test_agents.py -v -s
```

## Test Categories

### TestWorkflow Class

The simplified test suite contains 4 essential tests:

1. **test_workflow_completes**: Verifies that the workflow completes without errors for basic input
2. **test_routing_appointment**: Tests routing to appointment agent with correct intent classification
3. **test_routing_followup**: Tests routing to followup agent for symptom reporting
4. **test_red_flag_detection**: Critical safety check - verifies RED flag symptoms (e.g., chest pain) trigger emergency response

## Test Design Principles

- **LLM-Independent**: Tests are designed to work with or without LLM access
- **Rule-Based Fallbacks**: When LLMs fail (rate limits, API errors), rule-based logic takes over
- **Resilient Assertions**: Tests verify workflow completion and basic functionality, not specific LLM responses
- **RED Flag Priority**: RED flag detection works with rule-based keyword matching, so critical safety checks always work

## Test Execution

The tests can be run successfully even when:
- OpenAI API rate limits are hit
- LLM providers are unavailable
- Network issues occur

This is because the system has robust rule-based fallbacks that ensure core functionality (especially RED flag detection) always works.

## Future Improvements

Consider adding:
1. **Mock LLM Responses**: Use pytest fixtures to mock LLM calls for more reliable tests
2. **Unit Tests**: Test individual functions without full workflow
3. **Performance Tests**: Measure response times
4. **Edge Case Tests**: Test boundary conditions
