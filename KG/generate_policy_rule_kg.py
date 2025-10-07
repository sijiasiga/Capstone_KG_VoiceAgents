import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import matplotlib.pyplot as plt
import networkx as nx


@dataclass
class PolicyCondition:
    """Represents a single condition from the SQL policy."""
    field_name: str
    operator: str
    value: str
    description: str
    section: str
    condition_type: str  # 'demographic', 'eligibility', 'requirement', 'procedure', 'diagnosis'


class PolicyRuleKGGenerator:
    """Generates a knowledge graph for policy rules with policy as center node."""

    def __init__(self, sql_path: str, data_dictionary_path: str, output_dir: Optional[str] = None):
        self.sql_path = Path(sql_path)
        self.data_dictionary_path = Path(data_dictionary_path)
        self.output_dir = Path(output_dir) if output_dir else self.sql_path.parent
        
        self.graph = nx.DiGraph()
        self.data_dictionary = {}
        self.conditions: List[PolicyCondition] = []
        
    def generate(self) -> Tuple[List[Dict], List[Dict]]:
        """Generate the policy rule knowledge graph."""
        # Load data dictionary
        self._load_data_dictionary()
        
        # Parse SQL to extract conditions
        sql_text = self._read_sql()
        self._parse_sql_conditions(sql_text)
        
        # Create the knowledge graph
        self._build_knowledge_graph()
        
        # Convert to JSON format
        nodes = [{"id": node, **data} for node, data in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **data} for u, v, data in self.graph.edges(data=True)]
        
        return nodes, edges
    
    def _load_data_dictionary(self) -> None:
        """Load the data dictionary JSON file."""
        with open(self.data_dictionary_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for field in data:
            self.data_dictionary[field['name']] = field
    
    def _read_sql(self) -> str:
        """Read the SQL file."""
        return self.sql_path.read_text(encoding='utf-8')
    
    def _parse_sql_conditions(self, sql_text: str) -> None:
        """Parse SQL WHERE clause to extract individual conditions."""
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.*?)(?=;|$)', sql_text, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return
        
        where_clause = where_match.group(1).strip()
        
        # Split by OR operators first (top level)
        or_conditions = self._split_by_operator(where_clause, 'OR')
        
        for or_condition in or_conditions:
            # Split by AND operators
            and_conditions = self._split_by_operator(or_condition, 'AND')
            
            for condition in and_conditions:
                condition = condition.strip()
                if not condition or condition in ['(', ')']:
                    continue
                
                # Parse individual condition
                parsed_condition = self._parse_individual_condition(condition)
                if parsed_condition:
                    self.conditions.append(parsed_condition)
    
    def _split_by_operator(self, text: str, operator: str) -> List[str]:
        """Split text by operator while respecting parentheses and quotes."""
        parts = []
        depth = 0
        in_string = False
        string_delim = ""
        start = 0
        
        i = 0
        while i < len(text):
            char = text[i]
            
            if in_string:
                if char == string_delim:
                    in_string = False
                i += 1
                continue
            
            if char in ['"', "'"]:
                in_string = True
                string_delim = char
                i += 1
                continue
            
            if char == '(':
                depth += 1
            elif char == ')':
                depth = max(depth - 1, 0)
            
            if depth == 0 and text[i:i+len(operator)].upper() == operator.upper():
                # Check word boundaries
                before = text[i-1] if i > 0 else ' '
                after = text[i+len(operator)] if i+len(operator) < len(text) else ' '
                
                if self._is_word_boundary(before) and self._is_word_boundary(after):
                    part = text[start:i].strip()
                    if part:
                        parts.append(part)
                    i += len(operator)
                    start = i
                    continue
            
            i += 1
        
        # Add the last part
        part = text[start:].strip()
        if part:
            parts.append(part)
        
        return parts if len(parts) > 1 else [text]
    
    def _is_word_boundary(self, char: str) -> bool:
        """Check if character is a word boundary."""
        return char.isspace() or char in '()'
    
    def _parse_individual_condition(self, condition: str) -> Optional[PolicyCondition]:
        """Parse an individual SQL condition."""
        condition = condition.strip()
        
        # Remove outer parentheses
        while condition.startswith('(') and condition.endswith(')'):
            condition = condition[1:-1].strip()
        
        # Skip empty conditions
        if not condition:
            return None
        
        # Pattern matching for different condition types
        patterns = [
            # Field comparison patterns
            (r'(\w+)\s*([><=!]+)\s*([^,\s]+)', self._parse_comparison),
            (r'(\w+)\s+IN\s*\(([^)]+)\)', self._parse_in_condition),
            (r'(\w+)\s*=\s*([^,\s]+)', self._parse_equals),
        ]
        
        for pattern, parser in patterns:
            match = re.search(pattern, condition, re.IGNORECASE)
            if match:
                return parser(match, condition)
        
        return None
    
    def _parse_comparison(self, match, full_condition: str) -> Optional[PolicyCondition]:
        """Parse comparison conditions like patient_age >= 18."""
        field_name = match.group(1)
        operator = match.group(2)
        value = match.group(3)
        
        return self._create_condition(field_name, operator, value, full_condition)
    
    def _parse_in_condition(self, match, full_condition: str) -> Optional[PolicyCondition]:
        """Parse IN conditions like procedure IN ('surgery1', 'surgery2')."""
        field_name = match.group(1)
        values_str = match.group(2)
        
        # Extract values from the IN clause
        values = re.findall(r"'([^']+)'", values_str)
        value = ', '.join(values) if values else values_str
        
        return self._create_condition(field_name, 'IN', value, full_condition)
    
    def _parse_equals(self, match, full_condition: str) -> Optional[PolicyCondition]:
        """Parse equals conditions like field = value."""
        field_name = match.group(1)
        value = match.group(2)
        
        return self._create_condition(field_name, '=', value, full_condition)
    
    def _create_condition(self, field_name: str, operator: str, value: str, full_condition: str) -> Optional[PolicyCondition]:
        """Create a PolicyCondition object."""
        # Clean up field name
        field_name = field_name.lower().strip()
        
        # Get field info from data dictionary
        field_info = self.data_dictionary.get(field_name, {})
        description = field_info.get('description', f'Field: {field_name}')
        section = field_info.get('section', 'Unknown')
        
        # Determine condition type based on section
        condition_type = self._get_condition_type(section, field_name)
        
        return PolicyCondition(
            field_name=field_name,
            operator=operator,
            value=value,
            description=description,
            section=section,
            condition_type=condition_type
        )
    
    def _get_condition_type(self, section: str, field_name: str) -> str:
        """Determine the condition type based on section and field name."""
        if section == 'Demographics':
            return 'demographic'
        elif section == 'Eligibility':
            return 'eligibility'
        elif section == 'Program Requirements':
            return 'requirement'
        elif 'procedure' in field_name.lower() or section == 'Procedures':
            return 'procedure'
        elif 'diagnosis' in field_name.lower() or section == 'Diagnosis':
            return 'diagnosis'
        else:
            return 'other'
    
    def _build_knowledge_graph(self) -> None:
        """Build the knowledge graph with policy as center node."""
        # Create policy center node
        policy_id = "policy_center"
        self.graph.add_node(
            policy_id,
            id=policy_id,
            type="Policy",
            label="Bariatric Surgery Policy",
            description="Policy rules for bariatric surgery eligibility",
            node_size=2000
        )
        
        # Group conditions by type
        condition_groups = {}
        for condition in self.conditions:
            if condition.condition_type not in condition_groups:
                condition_groups[condition.condition_type] = []
            condition_groups[condition.condition_type].append(condition)
        
        # Create group nodes and condition nodes
        group_positions = {}
        angle_step = 2 * math.pi / len(condition_groups)
        
        for i, (condition_type, conditions) in enumerate(condition_groups.items()):
            # Create group node
            group_id = f"group_{condition_type}"
            group_angle = i * angle_step
            group_x = 3 * math.cos(group_angle)
            group_y = 3 * math.sin(group_angle)
            
            self.graph.add_node(
                group_id,
                id=group_id,
                type="ConditionGroup",
                label=f"{condition_type.title()} Conditions",
                condition_type=condition_type,
                node_size=1500
            )
            
            # Connect group to policy
            self.graph.add_edge(
                policy_id, group_id,
                relation="contains",
                edge_type="policy_rule"
            )
            
            # Create individual condition nodes
            condition_angle_step = angle_step / len(conditions)
            for j, condition in enumerate(conditions):
                condition_id = f"condition_{condition.field_name}_{j}"
                condition_angle = group_angle + (j - len(conditions)/2) * condition_angle_step
                condition_x = group_x + 1.5 * math.cos(condition_angle)
                condition_y = group_y + 1.5 * math.sin(condition_angle)
                
                # Create condition label
                condition_label = f"{condition.field_name} {condition.operator} {condition.value}"
                if len(condition_label) > 30:
                    condition_label = condition_label[:27] + "..."
                
                self.graph.add_node(
                    condition_id,
                    id=condition_id,
                    type="Condition",
                    label=condition_label,
                    field_name=condition.field_name,
                    operator=condition.operator,
                    value=condition.value,
                    description=condition.description,
                    section=condition.section,
                    condition_type=condition.condition_type,
                    node_size=1000
                )
                
                # Connect condition to group
                self.graph.add_edge(
                    group_id, condition_id,
                    relation="contains",
                    edge_type="group_condition"
                )
    
    def plot(self, output_path: Optional[str] = None, show: bool = False) -> Optional[Path]:
        """Plot the knowledge graph."""
        if not self.graph.nodes:
            raise RuntimeError("Graph is empty. Call generate() before plotting.")
        
        # Use spring layout for better positioning
        pos = nx.spring_layout(self.graph, k=3, iterations=50, seed=42)
        
        # Define colors for different node types
        colors = {
            "Policy": "#FF6B6B",  # Red for policy center
            "ConditionGroup": "#4ECDC4",  # Teal for groups
            "Condition": "#45B7D1",  # Blue for conditions
        }
        
        # Get node colors and sizes
        node_colors = []
        node_sizes = []
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'Condition')
            node_colors.append(colors.get(node_type, "#95A5A6"))
            node_sizes.append(self.graph.nodes[node].get('node_size', 1000))
        
        # Create the plot
        plt.figure(figsize=(16, 12))
        
        # Draw nodes
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.8
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            self.graph, pos,
            edge_color="#34495E",
            arrows=True,
            arrowsize=20,
            arrowstyle='->',
            alpha=0.6,
            width=2
        )
        
        # Draw labels
        labels = {node: data.get('label', node) for node, data in self.graph.nodes(data=True)}
        nx.draw_networkx_labels(
            self.graph, pos, labels,
            font_size=8,
            font_weight='bold'
        )
        
        # Create legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', label='Policy', 
                      markerfacecolor=colors['Policy'], markersize=15),
            plt.Line2D([0], [0], marker='o', color='w', label='Condition Groups', 
                      markerfacecolor=colors['ConditionGroup'], markersize=12),
            plt.Line2D([0], [0], marker='o', color='w', label='Conditions', 
                      markerfacecolor=colors['Condition'], markersize=10)
        ]
        plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        plt.title("Policy Rule Knowledge Graph\nBariatric Surgery Eligibility Criteria", 
                 fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        
        # Save plot if path provided
        saved_path = None
        if output_path:
            saved_path = Path(output_path)
            saved_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(saved_path, dpi=300, bbox_inches='tight')
            print(f"Policy rule KG plot saved to: {saved_path}")
        
        if show:
            plt.show()
        
        plt.close()
        return saved_path
    
    def save_json(self, nodes_filename: str = "policy_rule_kg_nodes.json", 
                  edges_filename: str = "policy_rule_kg_edges.json") -> Tuple[Path, Path]:
        """Save the knowledge graph as JSON files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        nodes_path = self.output_dir / nodes_filename
        edges_path = self.output_dir / edges_filename
        
        # Convert to JSON format
        nodes = [{"id": node, **data} for node, data in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **data} for u, v, data in self.graph.edges(data=True)]
        
        with open(nodes_path, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, indent=2, ensure_ascii=False)
        
        with open(edges_path, 'w', encoding='utf-8') as f:
            json.dump(edges, f, indent=2, ensure_ascii=False)
        
        return nodes_path, edges_path


def main():
    """Main function to run the policy rule KG generator."""
    parser = argparse.ArgumentParser(description="Generate policy rule knowledge graph")
    parser.add_argument("--sql", required=True, help="Path to SQL file")
    parser.add_argument("--data-dict", required=True, help="Path to data dictionary JSON file")
    parser.add_argument("--output-dir", help="Output directory (default: same as SQL file)")
    parser.add_argument("--plot-path", help="Path to save the plot (default: policy_rule_kg.png)")
    parser.add_argument("--show-plot", action="store_true", help="Show the plot")
    
    args = parser.parse_args()
    
    # Set default output directory
    if not args.output_dir:
        args.output_dir = Path(args.sql).parent
    
    # Set default plot path
    if not args.plot_path:
        args.plot_path = str(Path(args.output_dir) / "policy_rule_kg.png")
    
    # Generate the knowledge graph
    generator = PolicyRuleKGGenerator(
        sql_path=args.sql,
        data_dictionary_path=args.data_dict,
        output_dir=args.output_dir
    )
    
    print("Generating policy rule knowledge graph...")
    nodes, edges = generator.generate()
    
    # Save JSON files
    nodes_path, edges_path = generator.save_json()
    print(f"Nodes saved to: {nodes_path}")
    print(f"Edges saved to: {edges_path}")
    print(f"Total nodes: {len(nodes)}")
    print(f"Total edges: {len(edges)}")
    
    # Generate and save plot
    if args.plot_path or args.show_plot:
        saved_path = generator.plot(output_path=args.plot_path, show=args.show_plot)
        if saved_path:
            print(f"Plot saved to: {saved_path}")


if __name__ == "__main__":
    main()
