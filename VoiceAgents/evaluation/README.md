# Agent Evaluation System

Comprehensive evaluation framework for the Voice Agents multi-agent system.

## Overview

This evaluation system provides:
- **Accuracy metrics** for each agent (orchestration, medication, follow-up)
- **Performance benchmarks** (response times, throughput)
- **Visual reports** (HTML dashboard with charts and tables)

## Files

### Test Data
- `test_dataset.json` - Labeled test cases for all agents (45 total tests)

### Scripts
- `evaluate_agents.py` - Main evaluation script for accuracy metrics
- `benchmark_performance.py` - Performance and response time benchmarking
- `generate_report.py` - HTML report generator

### Results
- `results/evaluation_results.json` - Detailed test results
- `results/summary_metrics.json` - Aggregated metrics
- `results/performance_benchmark.json` - Performance data
- `results/evaluation_report.html` - **Visual dashboard**

## Quick Start

### 1. Run Full Evaluation

```bash
cd VoiceAgents/evaluation
python evaluate_agents.py
```

**Output:**
```
Orchestration Accuracy: 100.0%
Medication Intent Accuracy: 100.0%
Medication Risk Accuracy: 60.0%
Follow-Up Severity Accuracy: 90.0%
```

### 2. Run Performance Benchmark

```bash
python benchmark_performance.py
```

**Output:**
```
MEDICATION Agent: Avg 2.375s
FOLLOWUP Agent: Avg 0.565s
APPOINTMENT Agent: Avg 2.384s
OVERALL: Avg 1.473s
```

### 3. Generate HTML Report

```bash
python generate_report.py
```

Then open `results/evaluation_report.html` in your browser.

## Metrics Explained

### Orchestration Agent
- **Routing Accuracy**: % of queries routed to correct agent
- **Avg Response Time**: Time to classify intent

### Medication Agent
- **Intent Accuracy**: % correct classification (side_effect, missed_dose, etc.)
- **Risk Accuracy**: % correct risk level (RED/ORANGE/GREEN)

### Follow-Up Agent
- **Severity Accuracy**: % correct extraction of severity (0-10 scale)
- **Risk Accuracy**: % correct triage (RED >= 7, ORANGE 5-6, GREEN < 5)

### Performance
- **Min/Max/Avg**: Response time statistics across 5 iterations
- **Std Dev**: Consistency of response times

## Current Results (Summary)

| Metric | Score |
|--------|-------|
| Orchestration Accuracy | 100.0% |
| Medication Intent | 100.0% |
| Medication Risk | 60.0% |
| Follow-Up Severity | 90.0% |
| Avg Response Time | 1.47s |

## For Midterm Presentation

### Recommended Slides

**Slide 1: Evaluation Framework**
- 3 levels: Agent, System, User
- 45 test cases across all agents

**Slide 2: Key Metrics**
- Show the summary table above
- Highlight 100% orchestration accuracy

**Slide 3: Performance Analysis**
- Response time comparison chart
- Rule-based vs LLM-based agents

**Slide 4: Findings**
- Strengths: Perfect routing, fast rule-based agents
- Improvements: Risk scoring calibration needed

### Demo Flow

1. Open `evaluation_report.html` to show visual dashboard
2. Run `python evaluate_agents.py` live to show testing
3. Discuss specific test cases that worked well
4. Address known limitations (risk scoring)

## Extending Tests

To add new test cases, edit `test_dataset.json`:

```json
{
  "medication_tests": [
    {
      "id": 11,
      "query": "YOUR NEW QUERY",
      "expected_intent": "side_effect",
      "expected_risk": "GREEN",
      "patient_id": "10004235"
    }
  ]
}
```

Then re-run `python evaluate_agents.py`.

## Troubleshooting

**"No module named ..."**
- Run from `VoiceAgents/evaluation` directory
- Ensure Python path includes parent directory

**"File not found"**
- Check that `test_dataset.json` exists
- Run evaluation scripts from `evaluation/` folder

**LLM not working**
- Verify `OPENAI_API_KEY` environment variable is set
- Check API key validity and quota

## Future Improvements

- [ ] Add confusion matrix visualization
- [ ] User acceptance testing framework
- [ ] A/B testing for LLM prompts
- [ ] Voice recognition (STT) accuracy tests
- [ ] Load testing for concurrent requests
