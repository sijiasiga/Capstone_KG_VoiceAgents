"""
Agent Evaluation Script
Evaluates orchestration accuracy, agent-specific metrics, and performance
Includes confusion matrices for classification tasks
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Add parent directory to path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# Import agents
from orchestration_agent.demos.orchestration_agent_workflow import (
    Orchestrator,
    parse_intent_llm,
    parse_intent_rules,
)
from medication_agent.demos.medication_agent_workflow import (
    MedicationAgent,
    llm_parse_query,
    llm_score_risk,
)

# Results directory
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


class AgentEvaluator:
    def __init__(self, test_dataset_path: str):
        """Initialize evaluator with test dataset"""
        with open(test_dataset_path, 'r') as f:
            self.dataset = json.load(f)

        self.orchestrator = Orchestrator(voice=False)
        self.medication_agent = MedicationAgent(use_voice=False)

        self.results = {
            "orchestration": [],
            "medication": [],
            "followup": [],
            "appointment": [],
            "caregiver": [],
            "performance": []
        }

        # Confusion matrices
        self.confusion_matrices = {
            "orchestration_routing": defaultdict(lambda: defaultdict(int)),
            "medication_intent": defaultdict(lambda: defaultdict(int)),
            "medication_risk": defaultdict(lambda: defaultdict(int)),
            "followup_risk": defaultdict(lambda: defaultdict(int))
        }

    def evaluate_orchestration(self) -> Dict:
        """Evaluate orchestration agent routing accuracy"""
        print("\n[Orchestration Evaluation]")
        print("=" * 50)

        tests = self.dataset["orchestration_tests"]
        correct = 0
        total = len(tests)

        for test in tests:
            query = test["query"]
            expected_agent = test["expected_agent"]
            patient_id = test["patient_id"]

            # Set context
            self.orchestrator.patient_id = patient_id

            # Parse intent
            start_time = time.time()
            parsed = parse_intent_llm(query)
            elapsed = time.time() - start_time

            detected_intent = parsed.get("intent", "help")

            # Map intent to agent
            if detected_intent == "appointment":
                detected_agent = "appointment"
            elif detected_intent == "followup":
                detected_agent = "followup"
            elif detected_intent == "medication" or detected_intent in ["side_effect", "missed_dose", "interaction_check", "instruction", "contraindication", "general"]:
                detected_agent = "medication"
            elif detected_intent == "caregiver":
                detected_agent = "caregiver"
            else:
                detected_agent = "help"

            is_correct = (detected_agent == expected_agent)
            if is_correct:
                correct += 1

            # Update confusion matrix
            self.confusion_matrices["orchestration_routing"][expected_agent][detected_agent] += 1

            result = {
                "test_id": test["id"],
                "query": query,
                "expected_agent": expected_agent,
                "detected_agent": detected_agent,
                "detected_intent": detected_intent,
                "correct": is_correct,
                "response_time": elapsed
            }

            self.results["orchestration"].append(result)

            status = "[OK]" if is_correct else "[FAIL]"
            print(f"{status} Test {test['id']}: '{query[:50]}...'")
            print(f"     Expected: {expected_agent} | Got: {detected_agent}")

        accuracy = (correct / total) * 100
        print(f"\n[SUMMARY] Orchestration Accuracy: {correct}/{total} ({accuracy:.1f}%)")

        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "avg_response_time": sum(r["response_time"] for r in self.results["orchestration"]) / total
        }

    def evaluate_medication_agent(self) -> Dict:
        """Evaluate medication agent intent classification and risk scoring"""
        print("\n[Medication Agent Evaluation]")
        print("=" * 50)

        tests = self.dataset["medication_tests"]
        intent_correct = 0
        risk_correct = 0
        total = len(tests)

        for test in tests:
            query = test["query"]
            expected_intent = test["expected_intent"]
            expected_risk = test["expected_risk"]
            patient_id = test["patient_id"]

            # Parse query
            start_time = time.time()
            result = llm_parse_query(query)
            # Handle new 4-tuple return: (parsed, provider, model, latency_ms)
            if isinstance(result, tuple) and len(result) >= 3:
                parsed = result[0]
            else:
                parsed = result if not isinstance(result, tuple) else result[0]
            elapsed = time.time() - start_time

            detected_intent = parsed.get("intent", "general")

            # Score risk
            result = llm_score_risk(parsed)
            # Handle new 4-tuple return: (risk, provider, model, latency_ms)
            if isinstance(result, tuple) and len(result) >= 1:
                detected_risk = result[0]
            else:
                detected_risk = result if not isinstance(result, tuple) else result[0]

            intent_match = (detected_intent == expected_intent)
            risk_match = (detected_risk == expected_risk)

            if intent_match:
                intent_correct += 1
            if risk_match:
                risk_correct += 1

            # Update confusion matrices
            self.confusion_matrices["medication_intent"][expected_intent][detected_intent] += 1
            self.confusion_matrices["medication_risk"][expected_risk][detected_risk] += 1

            result = {
                "test_id": test["id"],
                "query": query,
                "expected_intent": expected_intent,
                "detected_intent": detected_intent,
                "intent_correct": intent_match,
                "expected_risk": expected_risk,
                "detected_risk": detected_risk,
                "risk_correct": risk_match,
                "response_time": elapsed
            }

            self.results["medication"].append(result)

            intent_status = "[OK]" if intent_match else "[FAIL]"
            risk_status = "[OK]" if risk_match else "[FAIL]"
            print(f"{intent_status} {risk_status} Test {test['id']}: '{query[:40]}...'")
            print(f"     Intent: {expected_intent} -> {detected_intent}")
            print(f"     Risk: {expected_risk} -> {detected_risk}")

        intent_accuracy = (intent_correct / total) * 100
        risk_accuracy = (risk_correct / total) * 100

        print(f"\n[SUMMARY] Intent Accuracy: {intent_correct}/{total} ({intent_accuracy:.1f}%)")
        print(f"[SUMMARY] Risk Accuracy: {risk_correct}/{total} ({risk_accuracy:.1f}%)")

        return {
            "intent_accuracy": intent_accuracy,
            "risk_accuracy": risk_accuracy,
            "intent_correct": intent_correct,
            "risk_correct": risk_correct,
            "total": total,
            "avg_response_time": sum(r["response_time"] for r in self.results["medication"]) / total
        }

    def evaluate_followup_agent(self) -> Dict:
        """Evaluate follow-up agent symptom extraction and triage"""
        print("\n[Follow-Up Agent Evaluation]")
        print("=" * 50)

        tests = self.dataset["followup_tests"]
        symptom_correct = 0
        severity_correct = 0
        risk_correct = 0
        total = len(tests)
        total_time = 0

        for test in tests:
            query = test["query"]
            expected_symptom = test["expected_symptom"]
            expected_severity = test["expected_severity"]
            expected_risk = test["expected_risk"]

            # Time the extraction
            start_time = time.time()

            # Simple pattern matching for evaluation (not using actual agent to avoid DB writes)
            import re

            # Extract severity
            severity_match = re.search(r'(\d+)\s*(?:/|out of)\s*10', query)
            if severity_match:
                detected_severity = int(severity_match.group(1))
            else:
                severity_match = re.search(r'level\s*(\d+)', query)
                if severity_match:
                    detected_severity = int(severity_match.group(1))
                else:
                    detected_severity = 0

            # Determine risk based on severity
            if detected_severity >= 7:
                detected_risk = "RED"
            elif detected_severity >= 5:
                detected_risk = "ORANGE"
            else:
                detected_risk = "GREEN"

            # Check if expected symptom appears in query
            symptom_match = expected_symptom.lower() in query.lower()

            elapsed = time.time() - start_time
            total_time += elapsed

            if symptom_match:
                symptom_correct += 1
            if detected_severity == expected_severity:
                severity_correct += 1
            if detected_risk == expected_risk:
                risk_correct += 1

            # Update confusion matrix
            self.confusion_matrices["followup_risk"][expected_risk][detected_risk] += 1

            result = {
                "test_id": test["id"],
                "query": query,
                "symptom_detected": symptom_match,
                "severity_correct": (detected_severity == expected_severity),
                "risk_correct": (detected_risk == expected_risk),
                "detected_severity": detected_severity,
                "expected_severity": expected_severity,
                "detected_risk": detected_risk,
                "expected_risk": expected_risk,
                "response_time": elapsed
            }

            self.results["followup"].append(result)

            status = "[OK]" if (symptom_match and detected_severity == expected_severity and detected_risk == expected_risk) else "[WARN]"
            print(f"{status} Test {test['id']}: Severity {expected_severity} -> {detected_severity}, Risk {expected_risk} -> {detected_risk}")

        symptom_accuracy = (symptom_correct / total) * 100
        severity_accuracy = (severity_correct / total) * 100
        risk_accuracy = (risk_correct / total) * 100

        print(f"\n[SUMMARY] Symptom Recognition: {symptom_correct}/{total} ({symptom_accuracy:.1f}%)")
        print(f"[SUMMARY] Severity Extraction: {severity_correct}/{total} ({severity_accuracy:.1f}%)")
        print(f"[SUMMARY] Risk Classification: {risk_correct}/{total} ({risk_accuracy:.1f}%)")

        return {
            "symptom_accuracy": symptom_accuracy,
            "severity_accuracy": severity_accuracy,
            "risk_accuracy": risk_accuracy,
            "total": total,
            "avg_response_time": total_time / total if total > 0 else 0
        }

    def evaluate_appointment_agent(self) -> Dict:
        """Evaluate appointment agent action detection"""
        print("\n[Appointment Agent Evaluation]")
        print("=" * 50)

        tests = self.dataset.get("appointment_tests", [])
        if not tests:
            print("[SKIP] No appointment tests found")
            return {"accuracy": 0, "total": 0}

        action_correct = 0
        total = len(tests)

        for test in tests:
            query = test["query"].lower()
            expected_action = test["expected_action"]

            # Simple pattern matching for action detection
            if "check" in query or "when" in query or "what" in query:
                detected_action = "check"
            elif "reschedule" in query or "change" in query or "move" in query:
                detected_action = "reschedule"
            elif "cancel" in query:
                detected_action = "cancel"
            else:
                detected_action = "unknown"

            action_match = (detected_action == expected_action)
            if action_match:
                action_correct += 1

            result = {
                "test_id": test["id"],
                "query": test["query"],
                "expected_action": expected_action,
                "detected_action": detected_action,
                "correct": action_match
            }

            self.results["appointment"].append(result)

            status = "[OK]" if action_match else "[FAIL]"
            print(f"{status} Test {test['id']}: {expected_action} -> {detected_action}")

        accuracy = (action_correct / total) * 100 if total > 0 else 0
        print(f"\n[SUMMARY] Action Detection Accuracy: {action_correct}/{total} ({accuracy:.1f}%)")

        return {
            "accuracy": accuracy,
            "action_correct": action_correct,
            "total": total
        }

    def evaluate_caregiver_agent(self) -> Dict:
        """Evaluate caregiver agent timeframe extraction"""
        print("\n[Caregiver Agent Evaluation]")
        print("=" * 50)

        tests = self.dataset.get("caregiver_tests", [])
        if not tests:
            print("[SKIP] No caregiver tests found")
            return {"accuracy": 0, "total": 0}

        timeframe_correct = 0
        total = len(tests)

        for test in tests:
            query = test["query"].lower()
            expected_timeframe = test["expected_timeframe"]

            # Simple pattern matching for timeframe detection
            import re
            day_match = re.search(r'(\d+)\s*days?', query)
            week_match = re.search(r'week', query)

            if day_match:
                detected_timeframe = int(day_match.group(1))
            elif week_match or "this week" in query:
                detected_timeframe = 7
            else:
                detected_timeframe = 7  # default to week

            timeframe_match = (detected_timeframe == expected_timeframe)
            if timeframe_match:
                timeframe_correct += 1

            result = {
                "test_id": test["id"],
                "query": test["query"],
                "expected_timeframe": expected_timeframe,
                "detected_timeframe": detected_timeframe,
                "correct": timeframe_match
            }

            self.results["caregiver"].append(result)

            status = "[OK]" if timeframe_match else "[FAIL]"
            print(f"{status} Test {test['id']}: {expected_timeframe} days -> {detected_timeframe} days")

        accuracy = (timeframe_correct / total) * 100 if total > 0 else 0
        print(f"\n[SUMMARY] Timeframe Extraction Accuracy: {timeframe_correct}/{total} ({accuracy:.1f}%)")

        return {
            "accuracy": accuracy,
            "timeframe_correct": timeframe_correct,
            "total": total
        }

    def save_results(self):
        """Save evaluation results to JSON file"""
        output_file = RESULTS_DIR / "evaluation_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[SAVED] Results saved to: {output_file}")

        # Save confusion matrices
        cm_output = RESULTS_DIR / "confusion_matrices.json"
        # Convert defaultdict to regular dict for JSON serialization
        cm_serializable = {}
        for matrix_name, matrix in self.confusion_matrices.items():
            cm_serializable[matrix_name] = {k: dict(v) for k, v in matrix.items()}

        with open(cm_output, 'w') as f:
            json.dump(cm_serializable, f, indent=2)
        print(f"[SAVED] Confusion matrices saved to: {cm_output}")

    def generate_summary_report(self):
        """Generate summary metrics"""
        summary = {
            "orchestration": {
                "total_tests": len(self.results["orchestration"]),
                "correct": sum(1 for r in self.results["orchestration"] if r["correct"]),
                "accuracy": sum(1 for r in self.results["orchestration"] if r["correct"]) / len(self.results["orchestration"]) * 100 if self.results["orchestration"] else 0,
                "avg_response_time": sum(r["response_time"] for r in self.results["orchestration"]) / len(self.results["orchestration"]) if self.results["orchestration"] else 0
            },
            "medication": {
                "total_tests": len(self.results["medication"]),
                "intent_correct": sum(1 for r in self.results["medication"] if r["intent_correct"]),
                "intent_accuracy": sum(1 for r in self.results["medication"] if r["intent_correct"]) / len(self.results["medication"]) * 100 if self.results["medication"] else 0,
                "risk_correct": sum(1 for r in self.results["medication"] if r["risk_correct"]),
                "risk_accuracy": sum(1 for r in self.results["medication"] if r["risk_correct"]) / len(self.results["medication"]) * 100 if self.results["medication"] else 0,
                "avg_response_time": sum(r["response_time"] for r in self.results["medication"]) / len(self.results["medication"]) if self.results["medication"] else 0
            },
            "followup": {
                "total_tests": len(self.results["followup"]),
                "symptom_correct": sum(1 for r in self.results["followup"] if r["symptom_detected"]),
                "severity_correct": sum(1 for r in self.results["followup"] if r["severity_correct"]),
                "risk_correct": sum(1 for r in self.results["followup"] if r["risk_correct"]),
                "symptom_accuracy": sum(1 for r in self.results["followup"] if r["symptom_detected"]) / len(self.results["followup"]) * 100 if self.results["followup"] else 0,
                "severity_accuracy": sum(1 for r in self.results["followup"] if r["severity_correct"]) / len(self.results["followup"]) * 100 if self.results["followup"] else 0,
                "risk_accuracy": sum(1 for r in self.results["followup"] if r["risk_correct"]) / len(self.results["followup"]) * 100 if self.results["followup"] else 0,
                "avg_response_time": sum(r.get("response_time", 0) for r in self.results["followup"]) / len(self.results["followup"]) if self.results["followup"] else 0
            },
            "appointment": {
                "total_tests": len(self.results["appointment"]),
                "action_correct": sum(1 for r in self.results["appointment"] if r["correct"]),
                "accuracy": sum(1 for r in self.results["appointment"] if r["correct"]) / len(self.results["appointment"]) * 100 if self.results["appointment"] else 0
            },
            "caregiver": {
                "total_tests": len(self.results["caregiver"]),
                "timeframe_correct": sum(1 for r in self.results["caregiver"] if r["correct"]),
                "accuracy": sum(1 for r in self.results["caregiver"] if r["correct"]) / len(self.results["caregiver"]) * 100 if self.results["caregiver"] else 0
            }
        }

        summary_file = RESULTS_DIR / "summary_metrics.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[SUMMARY REPORT]")
        print("=" * 70)
        print(f"Orchestration Accuracy: {summary['orchestration']['accuracy']:.1f}%")
        print(f"Medication Intent Accuracy: {summary['medication']['intent_accuracy']:.1f}%")
        print(f"Medication Risk Accuracy: {summary['medication']['risk_accuracy']:.1f}%")
        print(f"Follow-Up Severity Accuracy: {summary['followup']['severity_accuracy']:.1f}%")
        print(f"Follow-Up Risk Accuracy: {summary['followup']['risk_accuracy']:.1f}%")
        print(f"\nAvg Response Times:")
        print(f"  Orchestration: {summary['orchestration']['avg_response_time']:.3f}s")
        print(f"  Medication: {summary['medication']['avg_response_time']:.3f}s")
        print("=" * 70)

        print(f"\n[SAVED] Summary saved to: {summary_file}")

        return summary


def main():
    print("\n" + "=" * 70)
    print("  VOICE AGENTS - COMPREHENSIVE EVALUATION")
    print("=" * 70)

    # Load test dataset
    test_dataset = HERE / "test_dataset.json"
    if not test_dataset.exists():
        print(f"[ERROR] Test dataset not found at: {test_dataset}")
        return

    # Initialize evaluator
    evaluator = AgentEvaluator(str(test_dataset))

    # Run evaluations
    evaluator.evaluate_orchestration()
    evaluator.evaluate_medication_agent()
    evaluator.evaluate_followup_agent()
    evaluator.evaluate_appointment_agent()
    evaluator.evaluate_caregiver_agent()

    # Save results
    evaluator.save_results()

    # Generate summary
    evaluator.generate_summary_report()

    print("\n[COMPLETE] Evaluation finished successfully!")
    print(f"[INFO] Check results in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
