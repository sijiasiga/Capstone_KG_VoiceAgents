"""
Generate HTML evaluation report with visualizations
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"


def load_results():
    """Load all evaluation results"""
    summary_file = RESULTS_DIR / "summary_metrics.json"
    perf_file = RESULTS_DIR / "performance_summary.json"
    cm_file = RESULTS_DIR / "confusion_matrices.json"

    with open(summary_file, 'r') as f:
        summary = json.load(f)

    with open(perf_file, 'r') as f:
        performance = json.load(f)

    # Load confusion matrices if they exist
    confusion_matrices = {}
    if cm_file.exists():
        with open(cm_file, 'r') as f:
            confusion_matrices = json.load(f)

    return summary, performance, confusion_matrices


def generate_confusion_matrix_html(matrix_name, matrix_data):
    """Generate HTML for a confusion matrix"""
    if not matrix_data:
        return "<p>No data available</p>"

    # Get all unique labels (predicted and actual)
    all_labels = sorted(set(list(matrix_data.keys()) + [pred for preds in matrix_data.values() for pred in preds.keys()]))

    if not all_labels:
        return "<p>No data available</p>"

    html = f"""
    <div class="confusion-matrix-container">
        <h4>{matrix_name}</h4>
        <table class="confusion-matrix">
            <thead>
                <tr>
                    <th class="cm-corner">Actual \\ Predicted</th>
"""
    for label in all_labels:
        html += f'                    <th class="cm-header">{label}</th>\n'
    html += """                </tr>
            </thead>
            <tbody>
"""

    # Generate rows
    for actual in all_labels:
        html += f'                <tr>\n'
        html += f'                    <td class="cm-label"><strong>{actual}</strong></td>\n'
        for predicted in all_labels:
            count = matrix_data.get(actual, {}).get(predicted, 0)
            # Color code: green for correct (diagonal), red for errors
            cell_class = "cm-correct" if actual == predicted else "cm-error"
            if count == 0:
                cell_class = "cm-zero"
            html += f'                    <td class="cm-cell {cell_class}">{count}</td>\n'
        html += '                </tr>\n'

    html += """            </tbody>
        </table>
    </div>
"""
    return html


def generate_html_report(summary, performance, confusion_matrices):
    """Generate HTML report"""
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Agents - Evaluation Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        h1 {{
            font-size: 36px;
            margin-bottom: 10px;
        }}

        .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .metric-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 24px;
            border-left: 4px solid #667eea;
        }}

        .metric-card h3 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }}

        .metric-label {{
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section-title {{
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 16px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 14px 16px;
            border-bottom: 1px solid #e9ecef;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}

        .badge-excellent {{
            background: #d4edda;
            color: #155724;
        }}

        .badge-good {{
            background: #d1ecf1;
            color: #0c5460;
        }}

        .badge-fair {{
            background: #fff3cd;
            color: #856404;
        }}

        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}

        /* Confusion Matrix Styles */
        .confusion-matrix-container {{
            margin: 20px 0;
        }}

        .confusion-matrix-container h4 {{
            margin-bottom: 12px;
            color: #667eea;
            font-size: 16px;
        }}

        .confusion-matrix {{
            width: 100%;
            max-width: 500px;
            margin: 0;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .confusion-matrix th.cm-corner {{
            background: #f8f9fa;
            color: #666;
            font-weight: 600;
            padding: 8px;
            border: 1px solid #dee2e6;
            text-align: left;
            font-size: 11px;
        }}

        .confusion-matrix th.cm-header {{
            background: #667eea;
            color: white;
            padding: 8px;
            text-align: center;
            font-weight: 600;
            border: 1px solid #5568d3;
            font-size: 12px;
        }}

        .confusion-matrix td.cm-label {{
            background: #f8f9fa;
            font-weight: 600;
            padding: 8px;
            border: 1px solid #dee2e6;
            white-space: nowrap;
        }}

        .confusion-matrix td.cm-cell {{
            text-align: center;
            padding: 12px 8px;
            border: 1px solid #dee2e6;
            font-weight: 600;
            min-width: 50px;
        }}

        .confusion-matrix td.cm-correct {{
            background: #d4edda;
            color: #155724;
        }}

        .confusion-matrix td.cm-error {{
            background: #f8d7da;
            color: #721c24;
        }}

        .confusion-matrix td.cm-zero {{
            background: #f8f9fa;
            color: #ccc;
        }}

        .cm-grid {{
            display: flex;
            flex-direction: column;
            gap: 40px;
            margin-top: 20px;
        }}

        .cm-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 40px;
        }}

        @media print {{
            body {{
                background: white;
            }}

            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Voice Agents Evaluation Report</h1>
            <p class="subtitle">Comprehensive Performance & Accuracy Analysis</p>
        </header>

        <div class="content">
            <!-- Summary Metrics -->
            <div class="section">
                <h2 class="section-title">Overall System Performance</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <h3>Orchestration</h3>
                        <div class="metric-value">{summary['orchestration']['accuracy']:.1f}%</div>
                        <div class="metric-label">Routing Accuracy</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {summary['orchestration']['accuracy']}%"></div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <h3>Medication Intent</h3>
                        <div class="metric-value">{summary['medication']['intent_accuracy']:.1f}%</div>
                        <div class="metric-label">Classification Accuracy</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {summary['medication']['intent_accuracy']}%"></div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <h3>Follow-Up Severity</h3>
                        <div class="metric-value">{summary['followup']['severity_accuracy']:.1f}%</div>
                        <div class="metric-label">Extraction Accuracy</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {summary['followup']['severity_accuracy']}%"></div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <h3>Avg Response Time</h3>
                        <div class="metric-value">{performance['overall']['avg_response_time']:.2f}s</div>
                        <div class="metric-label">All Agents Combined</div>
                    </div>
                </div>
            </div>

            <!-- Agent-by-Agent Breakdown -->
            <div class="section">
                <h2 class="section-title">Agent Performance Breakdown</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Primary Metric</th>
                            <th>Accuracy</th>
                            <th>Avg Response Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Orchestration</strong></td>
                            <td>Intent Routing</td>
                            <td>{summary['orchestration']['accuracy']:.1f}%</td>
                            <td>{summary['orchestration']['avg_response_time']:.3f}s</td>
                            <td><span class="badge badge-excellent">Excellent</span></td>
                        </tr>
                        <tr>
                            <td><strong>Medication</strong></td>
                            <td>Intent + Risk</td>
                            <td>
                                <div style="margin-bottom: 4px;"><strong>Intent:</strong> {summary['medication']['intent_accuracy']:.1f}%</div>
                                <div><strong>Risk:</strong> {summary['medication']['risk_accuracy']:.1f}%</div>
                            </td>
                            <td>{summary['medication']['avg_response_time']:.3f}s</td>
                            <td><span class="badge {'badge-excellent' if summary['medication']['intent_accuracy'] >= 90 else 'badge-good'}">{'Excellent' if summary['medication']['intent_accuracy'] >= 90 else 'Good'}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Follow-Up</strong></td>
                            <td>Severity + Risk</td>
                            <td>
                                <div style="margin-bottom: 4px;"><strong>Severity:</strong> {summary['followup']['severity_accuracy']:.1f}%</div>
                                <div><strong>Risk:</strong> {summary['followup']['risk_accuracy']:.1f}%</div>
                            </td>
                            <td>{summary['followup']['avg_response_time']:.3f}s</td>
                            <td><span class="badge badge-excellent">Excellent</span></td>
                        </tr>
                        <tr>
                            <td><strong>Appointment</strong></td>
                            <td>Action Detection</td>
                            <td>{summary.get('appointment', {}).get('accuracy', 0):.1f}%</td>
                            <td>{performance['appointment']['avg_response_time']:.3f}s</td>
                            <td><span class="badge {'badge-excellent' if summary.get('appointment', {}).get('accuracy', 0) >= 90 else 'badge-good'}">{'Excellent' if summary.get('appointment', {}).get('accuracy', 0) >= 90 else 'Good'}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Caregiver</strong></td>
                            <td>Timeframe Extraction</td>
                            <td>{summary.get('caregiver', {}).get('accuracy', 0):.1f}%</td>
                            <td>{performance['caregiver']['avg_response_time']:.3f}s</td>
                            <td><span class="badge {'badge-excellent' if summary.get('caregiver', {}).get('accuracy', 0) >= 90 else 'badge-good'}">{'Excellent' if summary.get('caregiver', {}).get('accuracy', 0) >= 90 else 'Good'}</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Response Time Comparison -->
            <div class="section">
                <h2 class="section-title">Response Time Analysis</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Min Time</th>
                            <th>Avg Time</th>
                            <th>Max Time</th>
                            <th>Tests</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Add performance rows
    for agent, metrics in performance.items():
        if agent == "overall":
            continue

        html += f"""
                        <tr>
                            <td><strong>{agent.title()}</strong></td>
                            <td>{metrics['min_response_time']:.3f}s</td>
                            <td>{metrics['avg_response_time']:.3f}s</td>
                            <td>{metrics['max_response_time']:.3f}s</td>
                            <td>{metrics['num_tests']}</td>
                        </tr>
"""

    html += f"""
                    </tbody>
                </table>
            </div>

            <!-- Confusion Matrices -->
            <div class="section">
                <h2 class="section-title">Confusion Matrices</h2>
                <p style="margin-bottom: 20px; color: #666;">
                    Detailed classification breakdown showing where the system makes correct predictions (green) and errors (red).
                </p>
                <div class="cm-grid">
"""

    # Add confusion matrices organized in rows
    if confusion_matrices:
        matrix_titles = {
            "orchestration_routing": "Orchestration: Agent Routing",
            "medication_intent": "Medication: Intent Classification",
            "medication_risk": "Medication: Risk Level",
            "followup_risk": "Follow-Up: Risk Triage"
        }

        # Row 1: Orchestration and Medication Intent
        html += '                    <div class="cm-row">\n'
        for key in ["orchestration_routing", "medication_intent"]:
            if key in confusion_matrices and confusion_matrices[key]:
                title = matrix_titles[key]
                html += generate_confusion_matrix_html(title, confusion_matrices[key])
        html += '                    </div>\n'

        # Row 2: Medication Risk and Follow-Up Risk
        html += '                    <div class="cm-row">\n'
        for key in ["medication_risk", "followup_risk"]:
            if key in confusion_matrices and confusion_matrices[key]:
                title = matrix_titles[key]
                html += generate_confusion_matrix_html(title, confusion_matrices[key])
        html += '                    </div>\n'
    else:
        html += "<p>No confusion matrix data available</p>"

    html += """
                </div>
            </div>

            <!-- Error Analysis -->
            <div class="section">
                <h2 class="section-title">Error Analysis: Medication Risk Scoring (60% Accuracy)</h2>
                <p style="margin-bottom: 20px; color: #666;">
                    Detailed analysis of the 4 failed test cases out of 10, revealing systematic patterns in LLM risk assessment.
                </p>

                <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #ffc107;">
                    <h3 style="margin-bottom: 12px; color: #856404;">
                        ⚠️ Over-Cautious Cases (ORANGE → RED): 2 Failures
                    </h3>
                    <div style="background: white; padding: 16px; border-radius: 6px; margin-bottom: 12px;">
                        <p style="margin-bottom: 8px;"><strong>Test #2:</strong> "I forgot to take my Furosemide"</p>
                        <p style="margin-bottom: 8px; color: #666;">
                            <span style="color: #856404;">Expected: ORANGE</span> |
                            <span style="color: #721c24;">Detected: RED</span>
                        </p>
                        <p style="font-size: 14px; color: #666; line-height: 1.6;">
                            <strong>Root Cause:</strong> LLM over-prioritizes missed doses of critical medications (Furosemide is a diuretic for heart failure).
                            While missing one dose warrants attention (ORANGE), it's not immediately life-threatening (RED). The prompt needs calibration
                            to distinguish between "needs follow-up" vs "emergency."
                        </p>
                    </div>
                    <div style="background: white; padding: 16px; border-radius: 6px;">
                        <p style="margin-bottom: 8px;"><strong>Test #8:</strong> "I skipped my morning dose of Furosemide"</p>
                        <p style="margin-bottom: 8px; color: #666;">
                            <span style="color: #856404;">Expected: ORANGE</span> |
                            <span style="color: #721c24;">Detected: RED</span>
                        </p>
                        <p style="font-size: 14px; color: #666; line-height: 1.6;">
                            <strong>Root Cause:</strong> Same pattern as Test #2 - LLM lacks nuance in distinguishing missed dose urgency levels.
                        </p>
                    </div>
                </div>

                <div style="background: #f8d7da; padding: 20px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #dc3545;">
                    <h3 style="margin-bottom: 12px; color: #721c24;">
                        🚨 Dangerous Under-Cautious Case (RED → GREEN): 1 Critical Failure
                    </h3>
                    <div style="background: white; padding: 16px; border-radius: 6px;">
                        <p style="margin-bottom: 8px;"><strong>Test #10:</strong> "I accidentally took 3 pills of Metformin today"</p>
                        <p style="margin-bottom: 8px; color: #666;">
                            <span style="color: #721c24;">Expected: RED</span> |
                            <span style="color: #155724;">Detected: GREEN</span>
                        </p>
                        <p style="font-size: 14px; color: #666; line-height: 1.6;">
                            <strong>Root Cause:</strong> LLM failed to recognize triple-dose overdose as high risk. This is the most critical failure -
                            overdoses should ALWAYS trigger RED alerts. The prompt needs explicit rules: "Any accidental overdose ≥2x prescribed dose = RED."
                        </p>
                        <p style="font-size: 14px; color: #d9534f; margin-top: 8px; font-weight: 600;">
                            ⚠️ High Priority Fix: Patient safety risk - overdoses must never be downgraded.
                        </p>
                    </div>
                </div>

                <div style="background: #d1ecf1; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8;">
                    <h3 style="margin-bottom: 12px; color: #0c5460;">
                        💡 Under-Cautious Case (ORANGE → GREEN): 1 Failure
                    </h3>
                    <div style="background: white; padding: 16px; border-radius: 6px;">
                        <p style="margin-bottom: 8px;"><strong>Test #6:</strong> "Is Metformin safe during pregnancy?"</p>
                        <p style="margin-bottom: 8px; color: #666;">
                            <span style="color: #856404;">Expected: ORANGE</span> |
                            <span style="color: #155724;">Detected: GREEN</span>
                        </p>
                        <p style="font-size: 14px; color: #666; line-height: 1.6;">
                            <strong>Root Cause:</strong> LLM interpreted this as an informational query rather than a contraindication concern.
                            Pregnancy-related medication questions should elevate risk level to ORANGE (requires medical consultation).
                            The prompt needs explicit contraindication keywords: "pregnancy," "breastfeeding," "allergies."
                        </p>
                    </div>
                </div>
            </div>

            <!-- Future Improvements -->
            <div class="section">
                <h2 class="section-title">Future Improvements & Recommendations</h2>
                <p style="margin-bottom: 20px; color: #666;">
                    Actionable strategies to improve medication risk scoring from 60% to 90%+ accuracy.
                </p>

                <div style="background: #f8f9fa; padding: 24px; border-radius: 8px; line-height: 1.8;">
                    <h3 style="margin-bottom: 16px; color: #667eea;">1. Refine LLM Prompts with Explicit Risk Criteria</h3>
                    <div style="background: white; padding: 16px; border-radius: 6px; margin-bottom: 20px; border-left: 3px solid #667eea;">
                        <p style="margin-bottom: 12px;"><strong>Current Issue:</strong> Prompts rely on implicit LLM reasoning without explicit risk thresholds.</p>
                        <p style="margin-bottom: 12px;"><strong>Proposed Solution:</strong></p>
                        <ul style="margin-left: 20px; margin-bottom: 12px;">
                            <li><strong>RED Criteria:</strong> Overdose ≥2x dose, severe side effects (chest pain, difficulty breathing), drug interactions with known contraindications</li>
                            <li><strong>ORANGE Criteria:</strong> Single missed dose of critical meds (Furosemide, insulin), pregnancy/breastfeeding questions, moderate side effects</li>
                            <li><strong>GREEN Criteria:</strong> General information queries, mild side effects (nausea, fatigue), timing/instruction questions</li>
                        </ul>
                        <p style="font-size: 14px; color: #666;"><strong>Expected Impact:</strong> +20-30% accuracy by reducing ambiguity in edge cases.</p>
                    </div>

                    <h3 style="margin-bottom: 16px; color: #667eea;">2. Add Few-Shot Examples for Edge Cases</h3>
                    <div style="background: white; padding: 16px; border-radius: 6px; margin-bottom: 20px; border-left: 3px solid #667eea;">
                        <p style="margin-bottom: 12px;"><strong>Current Issue:</strong> LLM lacks training on specific overdose/contraindication patterns.</p>
                        <p style="margin-bottom: 12px;"><strong>Proposed Solution:</strong></p>
                        <ul style="margin-left: 20px; margin-bottom: 12px;">
                            <li>Include 3-5 few-shot examples in the prompt for each risk category</li>
                            <li>Example: "I took 3 pills of X" → RED (overdose pattern)</li>
                            <li>Example: "Is X safe during pregnancy?" → ORANGE (contraindication pattern)</li>
                            <li>Example: "I missed one dose of Y" → ORANGE if critical med, GREEN otherwise</li>
                        </ul>
                        <p style="font-size: 14px; color: #666;"><strong>Expected Impact:</strong> +15-20% accuracy through better pattern recognition.</p>
                    </div>

                    <h3 style="margin-bottom: 16px; color: #667eea;">3. Implement Rule-Based Safety Net</h3>
                    <div style="background: white; padding: 16px; border-radius: 6px; margin-bottom: 20px; border-left: 3px solid #667eea;">
                        <p style="margin-bottom: 12px;"><strong>Current Issue:</strong> Pure LLM approach has no failsafe for critical scenarios.</p>
                        <p style="margin-bottom: 12px;"><strong>Proposed Solution:</strong></p>
                        <ul style="margin-left: 20px; margin-bottom: 12px;">
                            <li>Add regex-based pre-screening for dangerous keywords: "overdose," "3 pills," "accidentally took too much"</li>
                            <li>If detected, override LLM output and force RED classification</li>
                            <li>Similarly, flag contraindication keywords: "pregnancy," "allergic," "reaction"</li>
                        </ul>
                        <p style="font-size: 14px; color: #666;"><strong>Expected Impact:</strong> Eliminates critical failures like Test #10 (100% safety on overdoses).</p>
                    </div>

                    <h3 style="margin-bottom: 16px; color: #667eea;">4. Expand Test Dataset to 100+ Cases</h3>
                    <div style="background: white; padding: 16px; border-radius: 6px; margin-bottom: 20px; border-left: 3px solid #667eea;">
                        <p style="margin-bottom: 12px;"><strong>Current Limitation:</strong> 10 medication tests may not cover all real-world scenarios.</p>
                        <p style="margin-bottom: 12px;"><strong>Proposed Solution:</strong></p>
                        <ul style="margin-left: 20px; margin-bottom: 12px;">
                            <li>Collect real patient queries from Zyter's post-discharge data (anonymized)</li>
                            <li>Include edge cases: multiple missed doses, complex interactions, polypharmacy (5+ medications)</li>
                            <li>Test across diverse patient demographics (elderly, pediatric, chronic conditions)</li>
                        </ul>
                        <p style="font-size: 14px; color: #666;"><strong>Expected Impact:</strong> More robust evaluation revealing hidden failure modes.</p>
                    </div>

                    <h3 style="margin-bottom: 16px; color: #667eea;">5. A/B Test Prompt Variations</h3>
                    <div style="background: white; padding: 16px; border-radius: 6px; border-left: 3px solid #667eea;">
                        <p style="margin-bottom: 12px;"><strong>Current Gap:</strong> Single prompt version limits optimization.</p>
                        <p style="margin-bottom: 12px;"><strong>Proposed Solution:</strong></p>
                        <ul style="margin-left: 20px; margin-bottom: 12px;">
                            <li>Create 3 prompt variants: (A) current, (B) with explicit criteria, (C) with few-shot + criteria</li>
                            <li>Run all 3 on expanded test dataset and compare accuracy</li>
                            <li>Measure precision/recall for each risk category to avoid over/under-cautious bias</li>
                        </ul>
                        <p style="font-size: 14px; color: #666;"><strong>Expected Impact:</strong> Data-driven prompt optimization (target: 90%+ accuracy).</p>
                    </div>
                </div>
            </div>

            <!-- Key Findings -->
            <div class="section">
                <h2 class="section-title">Key Findings Summary</h2>
                <div style="background: #f8f9fa; padding: 24px; border-radius: 8px; line-height: 1.8;">
                    <h3 style="margin-bottom: 16px;">Strengths</h3>
                    <ul style="margin-left: 20px; margin-bottom: 24px;">
                        <li><strong>Perfect Orchestration:</strong> 100% accuracy in routing queries to the correct agent (15/15 tests)</li>
                        <li><strong>Excellent Intent Classification:</strong> Medication agent achieves 100% intent recognition (10/10 tests)</li>
                        <li><strong>Fast Rule-Based Agents:</strong> Follow-up and caregiver agents respond in <1ms</li>
                        <li><strong>High Severity Detection:</strong> 90% accuracy in extracting symptom severity from natural language (9/10 tests)</li>
                        <li><strong>Perfect Risk Triage:</strong> Follow-up agent achieves 100% risk classification (10/10 tests)</li>
                    </ul>

                    <h3 style="margin-bottom: 16px;">Areas for Improvement</h3>
                    <ul style="margin-left: 20px;">
                        <li><strong>Medication Risk Scoring:</strong> 60% accuracy (6/10) - needs prompt refinement and safety rules (see Error Analysis above)</li>
                        <li><strong>Response Time Variance:</strong> LLM-based agents show 2-4s range - consider caching common queries</li>
                        <li><strong>Severity Pattern Matching:</strong> Follow-up agent missed "severity 4" format without "/" or "out of" - regex needs enhancement</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>Generated on {Path(RESULTS_DIR / 'summary_metrics.json').stat().st_mtime}</p>
            <p style="margin-top: 8px;">CMU x Zyter Capstone Project - Voice Agents for Post-Discharge Care</p>
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    print("[INFO] Loading evaluation results...")
    summary, performance, confusion_matrices = load_results()

    print("[INFO] Generating HTML report...")
    html = generate_html_report(summary, performance, confusion_matrices)

    output_file = RESULTS_DIR / "evaluation_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[SUCCESS] Report generated: {output_file}")
    print(f"[TIP] Open in browser: file:///{output_file}")


if __name__ == "__main__":
    main()
