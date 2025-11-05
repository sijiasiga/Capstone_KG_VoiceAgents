# Evaluation Module

Evaluation scripts for LangGraph VoiceAgents implementation.

## Quick Start

**From inside VoiceAgents_langgraph/ directory:**

```bash
cd VoiceAgents_langgraph

# Run main evaluation
python evaluation/evaluate_langgraph.py
```

## Files

- **evaluate_langgraph.py** - Main evaluation script (use this one)
  - Tests orchestration routing
  - Tests medication agent intent and risk classification
  - Runs end-to-end workflow tests
  - Generates confusion matrices

- **benchmark_performance.py** - Performance benchmarking
```bash
python evaluation/benchmark_performance.py
```

- **generate_report.py** - Generate HTML evaluation report
```bash
python evaluation/generate_report.py
```

- **evaluate_agents.py** - Original evaluation script (may require parent directory)

- **test_dataset.json** - Test dataset (required for evaluation)

## Usage

### Run Main Evaluation

```bash
# From VoiceAgents_langgraph/ directory
python evaluation/evaluate_langgraph.py
```

This will:
1. Load `test_dataset.json`
2. Run tests for orchestration, medication, and end-to-end workflows
3. Display results in console
4. Save detailed results to `evaluation/results/`

### Results

All results are saved to `evaluation/results/`:
- **evaluation_results.json** - Detailed test results with accuracy metrics
- **confusion_matrices.json** - Confusion matrices for classification tasks
- **performance_benchmark.json** - Performance metrics (from benchmark script)
- **evaluation_report.html** - HTML report (if generated)

### Sample Output

```
[Orchestration Evaluation]
==================================================
[OK] Test 1: 'check my appointment...'
     Expected: appointment | Got: appointment
...

[SUMMARY] Orchestration Accuracy: 18/20 (90.0%)

[Medication Agent Evaluation]
==================================================
[OK] [OK] Test 1: 'what are the side effects...'
     Intent: side_effect -> side_effect
     Risk: GREEN -> GREEN
...

[SAVED] Results saved to: evaluation/results/evaluation_results.json
[SAVED] Confusion matrices saved to: evaluation/results/confusion_matrices.json
```
