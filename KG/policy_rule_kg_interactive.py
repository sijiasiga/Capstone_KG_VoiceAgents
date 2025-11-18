"""
Interactive Policy Rule Knowledge Graph Visualization using Plotly
Supports zooming and dragging, with full node information display
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import networkx as nx
import plotly.graph_objects as go
from policy_rule_kg import PolicyRuleKGGenerator


class InteractivePolicyKGVisualizer:
    """Generate interactive policy rule knowledge graph using Plotly."""

    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        """
        Initialize with nodes and edges from PolicyRuleKGGenerator.

        Args:
            nodes: List of node dictionaries with 'id' and node attributes
            edges: List of edge dictionaries with 'source', 'target' and attributes
        """
        self.nodes = nodes
        self.edges = edges
        self.graph = self._build_networkx_graph()
        self.pos = self._get_spring_layout()

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

    def _get_spring_layout(self) -> Dict:
        """Get hierarchical radial layout with center node."""
        import math

        pos = {}

        # Find the center node (Policy node)
        center_node = None
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'Policy':
                center_node = node
                break

        if not center_node:
            # Fallback to spring layout if no policy node found
            return nx.spring_layout(self.graph, k=2, iterations=50, seed=42)

        # Place center node at origin
        pos[center_node] = (0, 0)

        # Get neighbors (ConditionGroup nodes)
        neighbors = list(self.graph.neighbors(center_node))
        num_groups = len(neighbors)

        if num_groups == 0:
            return pos

        # Place ConditionGroup nodes in a circle around center
        group_radius = 3.0
        angle_step = 2 * math.pi / num_groups

        group_positions = {}
        for i, group_node in enumerate(neighbors):
            angle = i * angle_step
            x = group_radius * math.cos(angle)
            y = group_radius * math.sin(angle)
            pos[group_node] = (x, y)
            group_positions[group_node] = (x, y)

        # Place Condition nodes around their parent ConditionGroup
        condition_radius = 1.2

        for group_node, (gx, gy) in group_positions.items():
            # Get children of this group (only outgoing edges from group to conditions)
            # Filter to only include Condition nodes
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

    def _get_node_color(self, node_type: str) -> str:
        """Get color based on node type."""
        colors = {
            "Policy": "#FF6B6B",
            "ConditionGroup": "#4ECDC4",
            "Condition": "#45B7D1",
        }
        return colors.get(node_type, "#95A5A6")

    def _get_node_size(self, node_type: str) -> int:
        """Get size based on node type."""
        sizes = {
            "Policy": 40,
            "ConditionGroup": 25,
            "Condition": 15,
        }
        return sizes.get(node_type, 15)

    def _create_hover_text(self, node_id: str) -> str:
        """Create detailed hover text for a node."""
        node_data = self.graph.nodes[node_id]

        hover_text = f"<b>{node_id}</b><br>"
        hover_text += f"<b>Type:</b> {node_data.get('type', 'Unknown')}<br>"

        if node_data.get('label'):
            hover_text += f"<b>Label:</b> {node_data.get('label')}<br>"

        if node_data.get('description'):
            description = node_data.get('description', '')
            if len(description) > 100:
                hover_text += f"<b>Description:</b> {description[:100]}...<br>"
            else:
                hover_text += f"<b>Description:</b> {description}<br>"

        if node_data.get('field_name'):
            hover_text += f"<b>Field:</b> {node_data.get('field_name')}<br>"

        if node_data.get('operator'):
            hover_text += f"<b>Operator:</b> {node_data.get('operator')}<br>"

        if node_data.get('value'):
            value = node_data.get('value', '')
            if len(value) > 100:
                hover_text += f"<b>Value:</b> {value[:100]}...<br>"
            else:
                hover_text += f"<b>Value:</b> {value}<br>"

        if node_data.get('section'):
            hover_text += f"<b>Section:</b> {node_data.get('section')}<br>"

        return hover_text

    def plot_interactive(self, output_path: Optional[str] = None) -> Optional[Path]:
        """
        Generate interactive Plotly visualization.

        Args:
            output_path: Path to save the HTML file

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

            node_colors.append(self._get_node_color(node_type))
            node_sizes.append(self._get_node_size(node_type))
            node_texts.append(self._create_hover_text(node_id))
            node_ids.append(node_id)

        # Prepare edge data
        edge_x = []
        edge_y = []

        for source, target in self.graph.edges():
            x0, y0 = self.pos[source]
            x1, y1 = self.pos[target]
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)

        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=1.5, color='#888'),
            hoverinfo='none',
            showlegend=False
        )

        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hovertext=node_texts,
            hoverinfo='text',
            text=[self.graph.nodes[node_id].get('label', node_id) for node_id in node_ids],
            textposition="top center",
            textfont=dict(size=10),
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

        # Update layout with legend
        fig.update_layout(
            title={
                'text': 'Policy Rule Knowledge Graph (Interactive)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=40),
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
        legend_y_positions = [0.95, 0.90, 0.85]
        colors_legend = {
            "Policy": "#FF6B6B",
            "Condition Groups": "#4ECDC4",
            "Conditions": "#45B7D1",
        }

        for i, (label, color) in enumerate(colors_legend.items()):
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
            print(f"Interactive policy KG plot saved to: {output_file}")
            return output_file

        return None


class PolicyRuleKGGenerator_WithInteractive(PolicyRuleKGGenerator):
    """Extended PolicyRuleKGGenerator with interactive visualization support."""

    def plot_interactive(self, output_path: Optional[str] = None) -> Optional[Path]:
        """Generate interactive plot using Plotly."""
        if not self.graph.nodes:
            raise RuntimeError("Graph is empty. Call generate() before plotting.")

        # Convert graph to nodes and edges format
        nodes = [{"id": node, **data} for node, data in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **data} for u, v, data in self.graph.edges(data=True)]

        # Create visualizer
        visualizer = InteractivePolicyKGVisualizer(nodes, edges)

        # Generate plot
        return visualizer.plot_interactive(output_path=output_path)

    def plot_static(self, output_path: Optional[str] = None, show: bool = False) -> Optional[Path]:
        """Generate static matplotlib plot (from original class)."""
        return self.plot(output_path=output_path, show=show)


def main():
    """Main function to run the interactive policy rule KG generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate interactive policy rule knowledge graph")
    parser.add_argument("--sql", required=True, help="Path to SQL file")
    parser.add_argument("--data-dict", required=True, help="Path to data dictionary JSON file")
    parser.add_argument("--policy-id", help="Policy identifier (default: policy_center)")
    parser.add_argument("--output-dir", help="Output directory (default: same as SQL file)")

    args = parser.parse_args()

    # Set default output directory
    if not args.output_dir:
        args.output_dir = Path(args.sql).parent

    # Generate the knowledge graph
    generator = PolicyRuleKGGenerator_WithInteractive(
        sql_path=args.sql,
        data_dictionary_path=args.data_dict,
        policy_id=args.policy_id,
        output_dir=args.output_dir
    )

    print("Generating interactive policy rule knowledge graph...")
    nodes, edges = generator.generate()

    # Generate and save interactive plot
    interactive_plot_path = str(Path(args.output_dir) / f"policy_rule_kg_interactive_{generator.policy_id}.html")
    saved_path = generator.plot_interactive(output_path=interactive_plot_path)
    if saved_path:
        print(f"Interactive plot saved to: {saved_path}")


if __name__ == "__main__":
    main()
