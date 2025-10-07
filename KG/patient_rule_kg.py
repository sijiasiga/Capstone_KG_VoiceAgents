#!/usr/bin/env python3
"""
Patient Rule Knowledge Graph Visualizer

Uses SQL for evaluation logic and Policy.json for descriptions.

Usage:
    python patient_rule_kg.py patient.json sql.txt policy.json --policy-id CGSURG83
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
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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
            # This is already valid Python syntax, just need to replace IN with in
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
    
    def create_visualization(self, figsize: Tuple[int, int] = (16, 12),
                            output_file: Optional[str] = None,
                            no_show: bool = False) -> None:
        """Create matplotlib visualization."""
        plt.figure(figsize=figsize)
        
        pos = nx.spring_layout(self.graph, k=3, iterations=50, seed=42)
        
        # Draw nodes
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            node_type = node_data.get('type', 'Condition')
            
            if node_type == 'Patient':
                color = self.color_schemes['patient']
                size = 2000
            elif node_type == 'ConditionGroup':
                color = self.color_schemes['condition_group']
                size = 1500
            elif node_type == 'Condition':
                logical_status = node_data.get('logical_status', 'not_met')
                if logical_status == 'met':
                    color = self.color_schemes['condition_met']
                elif logical_status == 'logically_met_by_other_or':
                    color = self.color_schemes['condition_logically_met']
                else:
                    color = self.color_schemes['condition_not_met']
                size = 1000
            else:
                color = self.color_schemes['default']
                size = 500
            
            nx.draw_networkx_nodes(
                self.graph, pos,
                nodelist=[node],
                node_color=color,
                node_size=size,
                alpha=0.8
            )
        
        # Draw edges
        met_edges = []
        logically_met_edges = []
        not_met_edges = []
        other_edges = []
        
        for edge in self.graph.edges():
            edge_data = self.graph.edges[edge]
            relation = edge_data.get('relation', '')
            
            if relation == 'met':
                met_edges.append(edge)
            elif relation == 'logically_met_by_other_or':
                logically_met_edges.append(edge)
            elif relation == 'not_met':
                not_met_edges.append(edge)
            else:
                other_edges.append(edge)
        
        if met_edges:
            nx.draw_networkx_edges(
                self.graph, pos, edgelist=met_edges,
                edge_color='green', alpha=0.8, width=3, style='-'
            )
        
        if logically_met_edges:
            nx.draw_networkx_edges(
                self.graph, pos, edgelist=logically_met_edges,
                edge_color='skyblue', alpha=0.8, width=3, style='-'
            )
        
        if not_met_edges:
            nx.draw_networkx_edges(
                self.graph, pos, edgelist=not_met_edges,
                edge_color='red', alpha=0.8, width=3, style='--'
            )
        
        if other_edges:
            nx.draw_networkx_edges(
                self.graph, pos, edgelist=other_edges,
                edge_color='gray', alpha=0.6, width=1.5
            )
        
        # Draw labels
        labels = {node: data.get('label', node) for node, data in self.graph.nodes(data=True)}
        nx.draw_networkx_labels(
            self.graph, pos, labels,
            font_size=8, font_weight='bold'
        )
        
        # Legend
        legend_elements = [
            mpatches.Patch(color=self.color_schemes['patient'], label='Patient'),
            mpatches.Patch(color=self.color_schemes['condition_group'], label='Rule Groups'),
            mpatches.Patch(color=self.color_schemes['condition_met'], label='Met'),
            mpatches.Patch(color=self.color_schemes['condition_logically_met'], label='Logically Met (OR)'),
            mpatches.Patch(color=self.color_schemes['condition_not_met'], label='Not Met'),
            plt.Line2D([0], [0], color='green', linewidth=3, label='Edge: Met'),
            plt.Line2D([0], [0], color='skyblue', linewidth=3, label='Edge: Logically Met'),
            plt.Line2D([0], [0], color='red', linewidth=3, linestyle='--', label='Edge: Not Met')
        ]
        plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        # Policy compliance status
        policy_met = self.evaluate_policy_compliance()
        policy_status = "✓ POLICY MET" if policy_met else "✗ POLICY NOT MET"
        policy_color = "green" if policy_met else "red"
        
        plt.title("Patient Rule Knowledge Graph\nPatient vs Policy Rules", 
                 fontsize=16, fontweight='bold', pad=20)
        
        plt.text(0.5, 0.98, policy_status, 
                transform=plt.gcf().transFigure,
                fontsize=14, fontweight='bold',
                color=policy_color,
                ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                         edgecolor=policy_color, linewidth=2))
        
        plt.axis('off')
        plt.tight_layout()
        
        # Save
        if output_file:
            output_path = f"{output_file}.png"
        else:
            output_path = "patient_rule_kg.png"
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 Patient rule knowledge graph saved as: {output_path}")
        
        if not no_show:
            plt.show()
    
    def generate_compliance_report(self, patient_id: str, policy_id: str, 
                                   output_dir: str = ".") -> str:
        """Generate compliance report JSON."""
        policy_met = self.evaluate_policy_compliance()
        
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
            'patient_id': patient_id,
            'policy_id': policy_id,
            'patient_met_policy': policy_met,
            'conditions': conditions_data
        }
        
        filename = f"pat_{patient_id}_pol_{policy_id}.json"
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
    parser = argparse.ArgumentParser(description="Patient Rule Knowledge Graph Visualizer")
    parser.add_argument('patient_file', help='Patient record JSON file')
    parser.add_argument('sql_file', help='SQL policy file')
    parser.add_argument('policy_file', help='Policy JSON file')
    parser.add_argument('--policy-id', type=str, default='POLICY', help='Policy ID')
    parser.add_argument('--output-file', type=str, help='Output file path (without extension)')
    parser.add_argument('--compliance-dir', type=str, default='.', help='Compliance report directory')
    parser.add_argument('--no-show', action='store_true', help='Do not display plot')
    parser.add_argument('--figsize', nargs=2, type=int, default=[16, 12], help='Figure size')
    
    args = parser.parse_args()
    
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
    print("🎨 Creating visualization...")
    visualizer.create_visualization(
        figsize=tuple(args.figsize),
        output_file=args.output_file,
        no_show=args.no_show
    )
    
    # Generate report
    print("\n📝 Generating compliance report...")
    os.makedirs(args.compliance_dir, exist_ok=True)
    visualizer.generate_compliance_report(patient_id, args.policy_id, args.compliance_dir)
    
    print("✅ Done!")


if __name__ == "__main__":
    main()