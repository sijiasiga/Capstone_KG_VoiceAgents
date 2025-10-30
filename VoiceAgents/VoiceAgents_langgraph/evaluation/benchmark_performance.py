"""
Performance Benchmark Script
Measures response times, throughput, and system performance metrics
"""

import os
import sys
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from orchestration_agent.demos.orchestration_agent_workflow import Orchestrator

# Results directory
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


class PerformanceBenchmark:
    def __init__(self):
        self.orchestrator = Orchestrator(voice=False)
        self.results = []

    def benchmark_single_query(self, query: str, patient_id: str = "10004235", iterations: int = 5) -> Dict:
        """Benchmark a single query multiple times"""
        times = []

        for i in range(iterations):
            self.orchestrator.patient_id = patient_id
            start = time.time()
            try:
                response = self.orchestrator.route(query)
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                print(f"[ERROR] Query failed: {e}")
                times.append(-1)

        # Filter out errors
        valid_times = [t for t in times if t > 0]

        if not valid_times:
            return {
                "query": query,
                "error": "All iterations failed",
                "iterations": iterations
            }

        return {
            "query": query,
            "iterations": iterations,
            "min_time": min(valid_times),
            "max_time": max(valid_times),
            "avg_time": statistics.mean(valid_times),
            "median_time": statistics.median(valid_times),
            "std_dev": statistics.stdev(valid_times) if len(valid_times) > 1 else 0
        }

    def run_benchmark_suite(self):
        """Run comprehensive performance benchmark"""
        print("\n" + "=" * 70)
        print("  PERFORMANCE BENCHMARK")
        print("=" * 70)

        test_queries = [
            ("What are the side effects of Metformin?", "medication"),
            ("I feel dizzy 7/10", "followup"),
            ("Check my appointment", "appointment"),
            ("Give me this week's caregiver update", "caregiver"),
            ("I forgot to take my Furosemide", "medication"),
            ("I have chest pain 9/10", "followup"),
        ]

        for query, agent_type in test_queries:
            print(f"\n[BENCHMARK] {agent_type.upper()} Agent")
            print(f"Query: '{query}'")

            result = self.benchmark_single_query(query)
            self.results.append({
                "agent_type": agent_type,
                **result
            })

            if "error" in result:
                print(f"[ERROR] {result['error']}")
            else:
                print(f"  Min: {result['min_time']:.3f}s")
                print(f"  Max: {result['max_time']:.3f}s")
                print(f"  Avg: {result['avg_time']:.3f}s")
                print(f"  Median: {result['median_time']:.3f}s")
                print(f"  Std Dev: {result['std_dev']:.3f}s")

    def generate_performance_summary(self) -> Dict:
        """Generate summary statistics by agent type"""
        summary = {}

        # Group by agent type
        by_agent = {}
        for result in self.results:
            if "error" in result:
                continue

            agent = result["agent_type"]
            if agent not in by_agent:
                by_agent[agent] = []
            by_agent[agent].append(result["avg_time"])

        # Calculate averages per agent
        for agent, times in by_agent.items():
            summary[agent] = {
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "num_tests": len(times)
            }

        # Overall statistics
        all_times = []
        for times in by_agent.values():
            all_times.extend(times)

        if all_times:
            summary["overall"] = {
                "avg_response_time": statistics.mean(all_times),
                "min_response_time": min(all_times),
                "max_response_time": max(all_times),
                "total_tests": len(all_times)
            }

        return summary

    def save_results(self):
        """Save benchmark results"""
        # Save detailed results
        results_file = RESULTS_DIR / "performance_benchmark.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[SAVED] Detailed results: {results_file}")

        # Save summary
        summary = self.generate_performance_summary()
        summary_file = RESULTS_DIR / "performance_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"[SAVED] Summary: {summary_file}")

        # Print summary
        print("\n" + "=" * 70)
        print("  PERFORMANCE SUMMARY")
        print("=" * 70)

        for agent, metrics in summary.items():
            if agent == "overall":
                continue
            print(f"\n{agent.upper()} Agent:")
            print(f"  Avg Response Time: {metrics['avg_response_time']:.3f}s")
            print(f"  Min: {metrics['min_response_time']:.3f}s")
            print(f"  Max: {metrics['max_response_time']:.3f}s")

        if "overall" in summary:
            print(f"\nOVERALL:")
            print(f"  Avg Response Time: {summary['overall']['avg_response_time']:.3f}s")
            print(f"  Total Tests: {summary['overall']['total_tests']}")

        print("=" * 70)


def main():
    benchmark = PerformanceBenchmark()
    benchmark.run_benchmark_suite()
    benchmark.save_results()
    print("\n[COMPLETE] Performance benchmark finished!")


if __name__ == "__main__":
    main()
