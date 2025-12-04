"""
Evaluation Script for LangGraph VoiceAgents
Adapted from original evaluate_agents.py to work with LangGraph structure
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Add package parent to sys.path so `import VoiceAgents_langgraph` works
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # .../VoiceAgents_langgraph
PARENT = ROOT.parent  # .../VoiceAgents
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

# Import LangGraph workflow
from VoiceAgents_langgraph.workflow import voice_agent_workflow
from VoiceAgents_langgraph.state import VoiceAgentState
from VoiceAgents_langgraph.nodes.routing import parse_intent_llm
from VoiceAgents_langgraph.nodes.medication import llm_parse_query, llm_score_risk

# Results directory
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


class LangGraphEvaluator:
    def __init__(self, test_dataset_path: str):
        """Initialize evaluator with test dataset"""
        with open(test_dataset_path, 'r') as f:
            self.dataset = json.load(f)

        self.results = {
            "orchestration": [],
            "medication": [],
            "followup": [],
            "appointment": [],
            "caregiver": [],
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
            patient_id = test.get("patient_id", "10004235")

            # Parse intent
            start_time = time.time()
            parsed = parse_intent_llm(query)
            elapsed = time.time() - start_time

            detected_intent = parsed.get("intent", "help")
            detected_pid = parsed.get("patient_id") or patient_id

            # Map intent to agent
            if detected_intent == "appointment":
                detected_agent = "appointment"
            elif detected_intent == "followup":
                detected_agent = "followup"
            elif detected_intent == "medication":
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
            patient_id = test.get("patient_id", "10004235")

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

    def evaluate_workflow_end_to_end(self) -> Dict:
        """Evaluate complete workflow end-to-end"""
        print("\n[End-to-End Workflow Evaluation]")
        print("=" * 50)

        tests = self.dataset.get("e2e_tests", [])
        if not tests:
            print("[SKIP] No end-to-end tests found")
            return {"accuracy": 0, "total": 0}

        correct = 0
        total = len(tests)

        for test in tests:
            query = test["query"]
            patient_id = test.get("patient_id", "10004235")
            expected_intent = test.get("expected_intent")

            # Initialize state
            initial_state: VoiceAgentState = {
                "user_input": query,
                "patient_id": patient_id,
                "intent": None,
                "parsed_data": {},
                "appointment_response": None,
                "followup_response": None,
                "medication_response": None,
                "caregiver_response": None,
                "help_response": None,
                "response": None,
                "voice_enabled": False,
                "session_id": f"eval_{test['id']}",
                "timestamp": None,
                "log_entry": None
            }

            # Run workflow
            start_time = time.time()
            try:
                final_state = voice_agent_workflow.invoke(initial_state)
                elapsed = time.time() - start_time
                
                detected_intent = final_state.get("intent")
                response = final_state.get("response", "")
                
                is_correct = (expected_intent is None) or (detected_intent == expected_intent)
                if is_correct:
                    correct += 1
                
                result = {
                    "test_id": test["id"],
                    "query": query,
                    "expected_intent": expected_intent,
                    "detected_intent": detected_intent,
                    "response": response[:100],  # First 100 chars
                    "correct": is_correct,
                    "response_time": elapsed
                }
                
                status = "[OK]" if is_correct else "[FAIL]"
                print(f"{status} Test {test['id']}: Intent {expected_intent} -> {detected_intent}")
                
            except Exception as e:
                result = {
                    "test_id": test["id"],
                    "query": query,
                    "error": str(e),
                    "correct": False
                }
                print(f"[ERROR] Test {test['id']}: {str(e)}")

        accuracy = (correct / total) * 100 if total > 0 else 0
        print(f"\n[SUMMARY] End-to-End Accuracy: {correct}/{total} ({accuracy:.1f}%)")

        return {
            "accuracy": accuracy,
            "correct": correct,
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
        cm_serializable = {}
        for matrix_name, matrix in self.confusion_matrices.items():
            cm_serializable[matrix_name] = {k: dict(v) for k, v in matrix.items()}

        with open(cm_output, 'w') as f:
            json.dump(cm_serializable, f, indent=2)
        print(f"[SAVED] Confusion matrices saved to: {cm_output}")


def main():
    print("\n" + "=" * 70)
    print("  LANGGRAPH VOICE AGENTS - COMPREHENSIVE EVALUATION")
    print("=" * 70)

    # Load test dataset
    test_dataset = HERE / "test_dataset.json"
    if not test_dataset.exists():
        print(f"[ERROR] Test dataset not found at: {test_dataset}")
        print(f"[INFO] Make sure test_dataset.json exists in evaluation/ directory")
        print(f"[INFO] Current directory: {HERE}")
        return

    # Initialize evaluator
    evaluator = LangGraphEvaluator(str(test_dataset))

    # Run evaluations
    evaluator.evaluate_orchestration()
    evaluator.evaluate_medication_agent()
    evaluator.evaluate_workflow_end_to_end()

    # Save results
    evaluator.save_results()

    print("\n[COMPLETE] Evaluation finished successfully!")
    print(f"[INFO] Check results in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()

