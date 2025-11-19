#!/usr/bin/env python3
"""
Interactive Patient Rule Knowledge Graph Visualizer using Plotly

Creates interactive visualizations showing patient data against policy rules.
Supports zooming and dragging, with full node information display.

Usage:
    python patient_rule_kg_interactive.py patient.json sql.txt policy.json --policy-id CGSURG83
"""

import json
import argparse
import sys
import os
import re
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import networkx as nx
import plotly.graph_objects as go
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


@dataclass
class PolicyCondition:
    """Represents a single condition from SQL."""
    condition: str  # Human-readable description from Policy.json
    rule: str  # SQL condition
    logic: str  # "AND" or "OR"
    is_met: bool = False
    logically_met: bool = False
    logical_status: str = "not_met"  # "met", "logically_met_by_other_or", "not_met"


class InteractivePatientRuleKGVisualizer:
    """Generate interactive patient rule knowledge graph using Plotly."""

    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        """
        Initialize with nodes and edges from PatientRuleKGVisualizer.

        Args:
            nodes: List of node dictionaries with 'id' and node attributes
            edges: List of edge dictionaries with 'source', 'target' and attributes
        """
        self.nodes = nodes
        self.edges = edges
        self.graph = self._build_networkx_graph()
        self.pos = self._get_hierarchical_layout()

    def _build_networkx_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from nodes and edges."""
        graph = nx.DiGraph()

        for node in self.nodes:
            node_id = node['id']
            node_attrs = {k: v for k, v in node.items() if k != 'id'}
            graph.add_node(node_id, **node_attrs)

        for edge in self.edges:
            source = edge['source']
            target = edge['target']
            edge_attrs = {k: v for k, v in edge.items() if k not in ['source', 'target']}
            graph.add_edge(source, target, **edge_attrs)

        return graph

    def _get_hierarchical_layout(self) -> Dict:
        """Get hierarchical layout with patient node at center."""
        import math

        pos = {}

        # Find the patient node
        patient_node = None
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'Patient':
                patient_node = node
                break

        if not patient_node:
            # Fallback to spring layout if no patient node found
            return nx.spring_layout(self.graph, k=2, iterations=50, seed=42)

        # Place patient node at origin
        pos[patient_node] = (0, 0)

        # Get condition group nodes
        group_nodes = [node for node, data in self.graph.nodes(data=True)
                      if data.get('type') == 'ConditionGroup']
        num_groups = len(group_nodes)

        if num_groups == 0:
            return pos

        # Place ConditionGroup nodes in a circle around patient
        group_radius = 3.0
        angle_step = 2 * math.pi / num_groups

        group_positions = {}
        for i, group_node in enumerate(group_nodes):
            angle = i * angle_step
            x = group_radius * math.cos(angle)
            y = group_radius * math.sin(angle)
            pos[group_node] = (x, y)
            group_positions[group_node] = (x, y)

        # Place Condition nodes around their parent ConditionGroup
        condition_radius = 1.2

        for group_node, (gx, gy) in group_positions.items():
            # Get children of this group (only condition nodes)
            children = [node for node in self.graph.neighbors(group_node)
                       if self.graph.nodes[node].get('type') == 'Condition']
            num_children = len(children)

            if num_children == 0:
                continue

            angle_step_child = 2 * math.pi / num_children

            for j, child_node in enumerate(children):
                child_angle = j * angle_step_child
                cx = gx + condition_radius * math.cos(child_angle)
                cy = gy + condition_radius * math.sin(child_angle)
                pos[child_node] = (cx, cy)

        return pos

    def _get_node_color(self, node_type: str, logical_status: str = None) -> str:
        """Get color based on node type and logical status."""
        if node_type == "Patient":
            return "#FF6B6B"  # Red
        elif node_type == "ConditionGroup":
            return "#4ECDC4"  # Teal
        elif node_type == "Condition":
            if logical_status == "met":
                return "#2ECC71"  # Green
            elif logical_status == "logically_met_by_other_or":
                return "#87CEEB"  # Sky blue
            else:
                return "#FF6B6B"  # Red
        return "#95A5A6"  # Gray

    def _get_node_size(self, node_type: str) -> int:
        """Get size based on node type."""
        sizes = {
            "Patient": 50,
            "ConditionGroup": 30,
            "Condition": 20,
        }
        return sizes.get(node_type, 20)

    def _create_hover_text(self, node_id: str) -> str:
        """Create detailed hover text for a node."""
        node_data = self.graph.nodes[node_id]

        hover_text = f"<b>{node_id}</b><br>"
        hover_text += f"<b>Type:</b> {node_data.get('type', 'Unknown')}<br>"

        if node_data.get('label'):
            hover_text += f"<b>Label:</b> {node_data.get('label')}<br>"

        if node_data.get('description'):
            description = node_data.get('description', '')
            if len(description) > 150:
                hover_text += f"<b>Description:</b> {description[:150]}...<br>"
            else:
                hover_text += f"<b>Description:</b> {description}<br>"

        if node_data.get('logic'):
            hover_text += f"<b>Logic:</b> {node_data.get('logic')}<br>"

        if node_data.get('is_met') is not None:
            status = "✓ Met" if node_data.get('is_met') else "✗ Not Met"
            hover_text += f"<b>Status:</b> {status}<br>"

        if node_data.get('logical_status'):
            hover_text += f"<b>Logical Status:</b> {node_data.get('logical_status')}<br>"

        return hover_text

    def plot_interactive(self, output_path: Optional[str] = None,
                         policy_met: bool = False, show_text: bool = True) -> Optional[Path]:
        """
        Generate interactive Plotly visualization.

        Args:
            output_path: Path to save the HTML file
            policy_met: Whether the patient met the policy
            show_text: Whether to show text labels on nodes (default: True)

        Returns:
            Path to the saved HTML file if successful
        """
        # Prepare node data
        node_x = []
        node_y = []
        node_colors = []
        node_sizes = []
        node_texts = []
        node_ids = []

        for node_id in self.graph.nodes():
            x, y = self.pos[node_id]
            node_x.append(x)
            node_y.append(y)

            node_data = self.graph.nodes[node_id]
            node_type = node_data.get('type', 'Condition')
            logical_status = node_data.get('logical_status', None)

            node_colors.append(self._get_node_color(node_type, logical_status))
            node_sizes.append(self._get_node_size(node_type))
            node_texts.append(self._create_hover_text(node_id))
            node_ids.append(node_id)

        # Prepare edge data
        edge_x = []
        edge_y = []
        edge_colors = []

        for source, target in self.graph.edges():
            x0, y0 = self.pos[source]
            x1, y1 = self.pos[target]
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)

            # Color edges based on relation type
            edge_data = self.graph.edges[source, target]
            relation = edge_data.get('relation', '')

            if relation == 'met':
                edge_colors.extend(['#2ECC71', '#2ECC71', None])  # Green
            elif relation == 'logically_met_by_other_or':
                edge_colors.extend(['#87CEEB', '#87CEEB', None])  # Sky blue
            elif relation == 'not_met':
                edge_colors.extend(['#FF6B6B', '#FF6B6B', None])  # Red
            else:
                edge_colors.extend(['#888', '#888', None])  # Gray

        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=1.5, color='#888'),
            hoverinfo='none',
            showlegend=False
        )

        # Create node trace - optionally show text labels
        mode = 'markers+text' if show_text else 'markers'
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode=mode,
            hovertext=node_texts,
            hoverinfo='text',
            text=[self.graph.nodes[node_id].get('label', node_id) for node_id in node_ids] if show_text else [],
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='white'),
                opacity=0.9
            ),
            showlegend=False
        )

        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace])

        # Calculate axis ranges with padding
        x_values = [x for x in node_x]
        y_values = [y for y in node_y]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        x_range = x_max - x_min
        y_range = y_max - y_min
        padding = 1.5

        # Policy compliance status
        policy_status = "✓ POLICY MET" if policy_met else "✗ POLICY NOT MET"
        policy_color = "green" if policy_met else "red"

        # Update layout
        fig.update_layout(
            title={
                'text': f'Patient Rule Knowledge Graph (Interactive)<br><span style="font-size:14px">{policy_status}</span>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=60),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=[x_min - padding, x_max + padding]
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=[y_min - padding, y_max + padding]
            ),
            plot_bgcolor='#f8f9fa',
            height=800,
            width=1200,
            dragmode='zoom'  # Allow panning and zooming
        )

        # Add legend manually
        legend_y_positions = [0.98, 0.93, 0.88, 0.83, 0.78]
        legend_items = [
            ("Patient", "#FF6B6B"),
            ("Condition Groups", "#4ECDC4"),
            ("Conditions Met", "#2ECC71"),
            ("Conditions Not Met", "#FF6B6B"),
            ("Logically Met (OR)", "#87CEEB"),
        ]

        for i, (label, color) in enumerate(legend_items):
            if i < len(legend_y_positions):
                fig.add_annotation(
                    x=0.02, y=legend_y_positions[i],
                    xref="paper", yref="paper",
                    text=f"<span style='color:{color}'>●</span> {label}",
                    showarrow=False,
                    xanchor='left',
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='#ccc',
                    borderwidth=1,
                    borderpad=4
                )

        # Save to file if path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(output_file))
            print(f"Interactive patient rule KG plot saved to: {output_file}")
            return output_file

        return None


class PatientRuleKGVisualizer:
    """Creates knowledge graphs showing patient data against policy rules."""

    def __init__(self, patient_data: Dict[str, Any], sql_text: str, policy_data: List[Dict[str, Any]]):
        """
        Initialize the visualizer.

        Args:
            patient_data: Patient record data
            sql_text: SQL policy text
            policy_data: Policy data with restrictions for descriptions
        """
        self.patient_data = patient_data
        self.sql_text = sql_text
        self.policy_data = policy_data
        self.conditions: List[PolicyCondition] = []
        self.graph = nx.DiGraph()

        # Build mapping from SQL rules to descriptions
        self.rule_to_description = {}
        for policy in policy_data:
            if 'restrictions' in policy:
                for restriction in policy['restrictions']:
                    rule = restriction.get('rule', '').strip()
                    condition_desc = restriction.get('condition', '')
                    logic = restriction.get('logic', 'AND')
                    if rule:
                        # Normalize for matching
                        normalized = rule.lower().replace(' ', '').replace('\n', '')
                        self.rule_to_description[normalized] = {
                            'description': condition_desc,
                            'logic': logic
                        }

        # Color schemes
        self.color_schemes = {
            'patient': '#FF6B6B',
            'condition_met': '#4ECDC4',
            'condition_logically_met': '#87CEEB',
            'condition_not_met': '#FF6B6B',
            'condition_group': '#45B7D1',
            'default': '#B0B0B0'
        }

    def normalize_rule(self, rule: str) -> str:
        """Normalize a rule for matching."""
        return rule.lower().replace(' ', '').replace('\n', '').replace('\t', '')

    def parse_and_evaluate_conditions(self) -> None:
        """Parse policy conditions and evaluate them using policy rules."""
        # Use Policy.json as the source of truth for conditions
        for policy in self.policy_data:
            if 'restrictions' not in policy:
                continue

            for restriction in policy['restrictions']:
                condition_text = restriction.get('condition', '')
                rule = restriction.get('rule', '')
                logic = restriction.get('logic', 'AND')

                # Evaluate the rule
                is_met = self.evaluate_condition(rule)

                condition = PolicyCondition(
                    condition=condition_text,
                    rule=rule,
                    logic=logic,
                    is_met=is_met
                )

                self.conditions.append(condition)

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a SQL condition against patient data."""
        try:
            # Build context with patient values
            context = {}
            for key, value in self.patient_data.items():
                context[key] = value
                context[key.lower()] = value

            # Prepare condition for evaluation
            eval_cond = condition.strip()

            # Handle IN clauses: convert SQL IN ('a','b') to Python in ('a','b')
            eval_cond = re.sub(r'\bIN\b', 'in', eval_cond, flags=re.IGNORECASE)

            # Handle boolean comparisons
            eval_cond = eval_cond.replace(' = TRUE', ' == True')
            eval_cond = eval_cond.replace(' = FALSE', ' == False')
            eval_cond = re.sub(r'\bTRUE\b', 'True', eval_cond)
            eval_cond = re.sub(r'\bFALSE\b', 'False', eval_cond)

            # Handle logical operators
            eval_cond = re.sub(r'\bAND\b', 'and', eval_cond)
            eval_cond = re.sub(r'\bOR\b', 'or', eval_cond)

            # Evaluate
            result = eval(eval_cond, {"__builtins__": {}}, context)
            return bool(result)
        except Exception as e:
            return False

    def apply_logical_operators(self) -> None:
        """Apply OR/AND logic to conditions."""
        and_conditions = [c for c in self.conditions if c.logic == 'AND']
        or_conditions = [c for c in self.conditions if c.logic == 'OR']

        # Check if any OR condition is met
        has_met_or = any(c.is_met for c in or_conditions) if or_conditions else False

        # Mark AND conditions
        for condition in and_conditions:
            condition.logically_met = condition.is_met
            condition.logical_status = 'met' if condition.is_met else 'not_met'

        # Mark OR conditions
        for condition in or_conditions:
            condition.logically_met = has_met_or
            if condition.is_met:
                condition.logical_status = 'met'
            elif has_met_or:
                condition.logical_status = 'logically_met_by_other_or'
            else:
                condition.logical_status = 'not_met'

    def evaluate_policy_compliance(self) -> bool:
        """Evaluate if patient meets overall policy."""
        and_conditions = [c for c in self.conditions if c.logic == 'AND']
        or_conditions = [c for c in self.conditions if c.logic == 'OR']

        and_satisfied = all(c.is_met for c in and_conditions) if and_conditions else True
        or_satisfied = any(c.is_met for c in or_conditions) if or_conditions else True

        return and_satisfied and or_satisfied

    def build_knowledge_graph(self) -> None:
        """Build the knowledge graph."""
        patient_id = self.patient_data.get('patient_id', 'unknown')
        patient_name = f"Patient {patient_id}"

        self.graph.add_node(
            patient_id,
            type="Patient",
            label=patient_name,
            node_size=2000
        )

        # Group by logic type
        and_conditions = [c for c in self.conditions if c.logic == 'AND']
        or_conditions = [c for c in self.conditions if c.logic == 'OR']

        condition_groups = {}
        if and_conditions:
            condition_groups['AND'] = and_conditions
        if or_conditions:
            condition_groups['OR'] = or_conditions

        # Create group nodes
        angle_step = 2 * math.pi / max(len(condition_groups), 1)

        for i, (logic_type, conditions) in enumerate(condition_groups.items()):
            group_id = f"group_{logic_type}"

            self.graph.add_node(
                group_id,
                type="ConditionGroup",
                label=f"{logic_type} Conditions",
                node_size=1500
            )

            self.graph.add_edge(
                patient_id, group_id,
                relation="evaluated_by",
                edge_type="patient_group"
            )

            # Create condition nodes
            for j, condition in enumerate(conditions):
                condition_id = f"condition_{logic_type}_{j}"

                label = condition.condition[:30] + "..." if len(condition.condition) > 30 else condition.condition
                status = "✓" if condition.is_met else "✗"
                label = f"{status} {label}"

                self.graph.add_node(
                    condition_id,
                    type="Condition",
                    label=label,
                    description=condition.condition,
                    logic=condition.logic,
                    is_met=condition.is_met,
                    logical_status=condition.logical_status,
                    node_size=1000
                )

                self.graph.add_edge(
                    group_id, condition_id,
                    relation="contains",
                    edge_type="group_condition"
                )

                edge_relation = condition.logical_status
                self.graph.add_edge(
                    patient_id, condition_id,
                    relation=edge_relation,
                    edge_type="patient_condition"
                )

    def plot_interactive(self, output_path: Optional[str] = None, show_text: bool = True) -> Optional[Path]:
        """Generate interactive plot using Plotly.

        Args:
            output_path: Path to save the HTML file
            show_text: Whether to show text labels on nodes (default: True)

        Returns:
            Path to the saved HTML file if successful
        """
        if not self.graph.nodes:
            raise RuntimeError("Graph is empty. Call build_knowledge_graph() before plotting.")

        # Convert graph to nodes and edges format
        nodes = [{"id": node, **data} for node, data in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **data} for u, v, data in self.graph.edges(data=True)]

        # Create visualizer
        visualizer = InteractivePatientRuleKGVisualizer(nodes, edges)

        # Get compliance status
        policy_met = self.evaluate_policy_compliance()

        # Generate plot
        return visualizer.plot_interactive(output_path=output_path, policy_met=policy_met, show_text=show_text)

    def generate_compliance_report(self, patient_id: str, policy_id: str,
                                   output_dir: str = ".") -> str:
        """Generate compliance report JSON."""
        import re

        policy_met = self.evaluate_policy_compliance()

        # Clean patient_id - remove all non-alphanumeric characters
        clean_patient_id = re.sub(r'[^a-zA-Z0-9]', '', str(patient_id))

        conditions_data = []
        for condition in self.conditions:
            conditions_data.append({
                'condition': condition.condition,
                'rule': condition.rule,
                'logic': condition.logic,
                'is_met': condition.is_met,
                'logically_met': condition.logically_met,
                'logical_status': condition.logical_status
            })

        report = {
            'patient_id': clean_patient_id,
            'policy_id': policy_id,
            'patient_met_policy': policy_met,
            'conditions': conditions_data
        }

        filename = f"pat_{clean_patient_id}_pol_{policy_id}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 Compliance report saved: {filepath}")
        return filepath


def load_json_file(file_path: str) -> Any:
    """Load JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        sys.exit(1)


def load_text_file(file_path: str) -> str:
    """Load text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Interactive Patient Rule Knowledge Graph Visualizer")
    parser.add_argument('patient_file', help='Patient record JSON file')
    parser.add_argument('--sql-file', type=str, help='SQL policy file')
    parser.add_argument('--policy-file', type=str, help='Policy JSON file')
    parser.add_argument('--policy-id', type=str, default='POLICY', help='Policy ID')
    parser.add_argument('--output-file', type=str, help='Output file path (without extension)')
    parser.add_argument('--no-show', action='store_true', help='Do not display plot')

    args = parser.parse_args()

    # Validate required arguments
    if not args.sql_file:
        print("❌ Error: --sql-file is required")
        parser.print_help()
        sys.exit(1)

    if not args.policy_file:
        print("❌ Error: --policy-file is required")
        parser.print_help()
        sys.exit(1)

    # Load data
    print(f"📁 Loading patient data: {args.patient_file}")
    patient_data = load_json_file(args.patient_file)

    print(f"📁 Loading SQL policy: {args.sql_file}")
    sql_text = load_text_file(args.sql_file)

    print(f"📁 Loading policy data: {args.policy_file}")
    policy_data = load_json_file(args.policy_file)

    patient_id = patient_data.get('patient_id', 'unknown')

    # Create visualizer
    print(f"\n🔧 Creating visualizer for patient {patient_id}...")
    visualizer = PatientRuleKGVisualizer(patient_data, sql_text, policy_data)

    # Parse and evaluate conditions from Policy.json
    print("🔍 Evaluating policy conditions...")
    visualizer.parse_and_evaluate_conditions()

    print("⚖️  Applying logical operators...")
    visualizer.apply_logical_operators()

    # Build graph
    print("🏗️  Building knowledge graph...")
    visualizer.build_knowledge_graph()

    # Visualize
    print("🎨 Creating interactive visualization...")
    visualizer.plot_interactive(output_path=args.output_file)

    print("✅ Done!")


if __name__ == "__main__":
    main()
