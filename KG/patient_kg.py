#!/usr/bin/env python3
"""
Patient Knowledge Graph Visualizer

A flexible tool that takes a JSON file as input and creates interactive knowledge graphs.
Supports various JSON structures and provides multiple visualization options.

Usage:
    python patient_kg.py input.json [options]

Author: AI Assistant
"""

import json
import argparse
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

class PatientKGVisualizer:
    """Main class for creating and visualizing patient knowledge graphs from JSON data."""
    
    def __init__(self, json_data: Dict[str, Any]):
        """
        Initialize the visualizer with JSON data.
        
        Args:
            json_data: Dictionary containing the JSON data to visualize
        """
        self.json_data = json_data
        self.graph = nx.Graph()
        self.node_colors = {}
        self.edge_colors = {}
        self.node_sizes = {}
        self.node_labels = {}
        self.edge_labels = {}
        
        # Color schemes for different node types
        self.color_schemes = {
            'patient': '#FF6B6B',      # Red
            'policy': '#4ECDC4',       # Teal
            'criterion': '#45B7D1',    # Blue
            'procedure': '#96CEB4',    # Green
            'diagnosis': '#FFEAA7',    # Yellow
            'comorbidity': '#DDA0DD',  # Plum
            'data_field': '#98D8C8',   # Mint
            'default': '#B0B0B0'       # Gray
        }
        
    def detect_data_structure(self) -> str:
        """
        Detect the structure of the JSON data to determine visualization strategy.
        
        Returns:
            String indicating the detected data structure type
        """
        if isinstance(self.json_data, dict):
            # Check for common patterns
            if 'patient_id' in self.json_data:
                return 'patient_record'
            elif 'name' in self.json_data and 'restrictions' in self.json_data:
                return 'policy'
            elif 'nodes' in self.json_data and 'edges' in self.json_data:
                return 'graph_structure'
            elif all(isinstance(v, (str, int, float, bool)) for v in self.json_data.values()):
                return 'simple_dict'
            else:
                return 'complex_dict'
        elif isinstance(self.json_data, list):
            if all(isinstance(item, dict) and 'name' in item for item in self.json_data):
                return 'data_dictionary'
            elif all(isinstance(item, dict) and 'source' in item and 'target' in item for item in self.json_data):
                return 'edge_list'
            else:
                return 'object_list'
        else:
            return 'unknown'
    
    def create_patient_record_graph(self) -> None:
        """Create graph from patient record data."""
        patient_id = self.json_data.get('patient_id', 'Unknown')
        
        # Add patient node
        self.graph.add_node(patient_id, type='patient', **self.json_data)
        self.node_colors[patient_id] = self.color_schemes['patient']
        self.node_sizes[patient_id] = 1000
        self.node_labels[patient_id] = f"Patient {patient_id}"
        
        # Add attribute nodes
        for key, value in self.json_data.items():
            if key != 'patient_id':
                attr_id = f"{patient_id}_{key}"
                self.graph.add_node(attr_id, type='attribute', field=key, value=value)
                self.graph.add_edge(patient_id, attr_id, relation='has_attribute')
                
                # Color based on value type
                if isinstance(value, bool):
                    self.node_colors[attr_id] = '#90EE90' if value else '#FFB6C1'
                elif isinstance(value, (int, float)):
                    self.node_colors[attr_id] = '#87CEEB'
                else:
                    self.node_colors[attr_id] = self.color_schemes['data_field']
                
                self.node_sizes[attr_id] = 500
                self.node_labels[attr_id] = f"{key}: {value}"
                self.edge_labels[(patient_id, attr_id)] = 'has'
    
    def create_policy_graph(self) -> None:
        """Create graph from policy data."""
        policy_name = self.json_data.get('name', 'Unknown Policy')
        policy_id = policy_name.replace(' ', '_').replace(',', '')
        
        # Add policy node
        self.graph.add_node(policy_id, type='policy', **self.json_data)
        self.node_colors[policy_id] = self.color_schemes['policy']
        self.node_sizes[policy_id] = 1200
        self.node_labels[policy_id] = policy_name
        
        # Add restriction/criteria nodes
        restrictions = self.json_data.get('restrictions', [])
        for idx, restriction in enumerate(restrictions):
            criterion_id = f"{policy_id}_criterion_{idx}"
            self.graph.add_node(criterion_id, type='criterion', **restriction)
            self.graph.add_edge(policy_id, criterion_id, relation='has_criterion')
            
            self.node_colors[criterion_id] = self.color_schemes['criterion']
            self.node_sizes[criterion_id] = 800
            self.node_labels[criterion_id] = restriction.get('condition', f'Criterion {idx}')
            self.edge_labels[(policy_id, criterion_id)] = 'requires'
            
            # Add codes if present
            codes = restriction.get('codes', [])
            for code in codes:
                code_id = f"code_{code}"
                if not self.graph.has_node(code_id):
                    self.graph.add_node(code_id, type='code', code=code)
                    self.node_colors[code_id] = self.color_schemes['procedure']
                    self.node_sizes[code_id] = 600
                    self.node_labels[code_id] = code
                
                self.graph.add_edge(criterion_id, code_id, relation='applies_to')
                self.edge_labels[(criterion_id, code_id)] = 'applies_to'
    
    def create_data_dictionary_graph(self) -> None:
        """Create graph from data dictionary list."""
        for idx, field in enumerate(self.json_data):
            field_name = field.get('name', f'field_{idx}')
            field_id = f"field_{field_name}"
            
            self.graph.add_node(field_id, type='data_field', **field)
            self.node_colors[field_id] = self.color_schemes['data_field']
            self.node_sizes[field_id] = 700
            self.node_labels[field_id] = field_name
            
            # Add section grouping
            section = field.get('section', 'Unknown')
            section_id = f"section_{section}"
            if not self.graph.has_node(section_id):
                self.graph.add_node(section_id, type='section', name=section)
                self.node_colors[section_id] = '#E6E6FA'  # Lavender
                self.node_sizes[section_id] = 900
                self.node_labels[section_id] = section
            
            self.graph.add_edge(section_id, field_id, relation='contains')
            self.edge_labels[(section_id, field_id)] = 'contains'
    
    def create_graph_structure_graph(self) -> None:
        """Create graph from pre-structured graph data (nodes and edges)."""
        # Add nodes
        for node in self.json_data.get('nodes', []):
            node_id = node.get('id', node.get('name', 'unknown'))
            self.graph.add_node(node_id, **node)
            
            node_type = node.get('type', 'default')
            self.node_colors[node_id] = self.color_schemes.get(node_type, self.color_schemes['default'])
            self.node_sizes[node_id] = 800
            self.node_labels[node_id] = node.get('name', node_id)
        
        # Add edges
        for edge in self.json_data.get('edges', []):
            source = edge.get('source')
            target = edge.get('target')
            relation = edge.get('relation', 'related_to')
            
            if source and target:
                self.graph.add_edge(source, target, **edge)
                self.edge_labels[(source, target)] = relation
    
    def create_simple_dict_graph(self) -> None:
        """Create graph from simple key-value dictionary."""
        center_id = 'root'
        self.graph.add_node(center_id, type='root')
        self.node_colors[center_id] = '#FFD700'  # Gold
        self.node_sizes[center_id] = 1000
        self.node_labels[center_id] = 'Root'
        
        for key, value in self.json_data.items():
            attr_id = f"attr_{key}"
            self.graph.add_node(attr_id, type='attribute', field=key, value=value)
            self.graph.add_edge(center_id, attr_id, relation='has_attribute')
            
            self.node_colors[attr_id] = self.color_schemes['data_field']
            self.node_sizes[attr_id] = 600
            self.node_labels[attr_id] = f"{key}: {value}"
            self.edge_labels[(center_id, attr_id)] = 'has'
    
    def create_object_list_graph(self) -> None:
        """Create graph from list of objects."""
        for idx, obj in enumerate(self.json_data):
            obj_id = f"obj_{idx}"
            obj_type = obj.get('type', 'object')
            
            self.graph.add_node(obj_id, type=obj_type, **obj)
            self.node_colors[obj_id] = self.color_schemes.get(obj_type, self.color_schemes['default'])
            self.node_sizes[obj_id] = 700
            self.node_labels[obj_id] = obj.get('name', f'Object {idx}')
            
            # Try to find relationships
            for key, value in obj.items():
                if isinstance(value, str) and any(other_obj.get('id') == value or other_obj.get('name') == value 
                                                for other_obj in self.json_data if other_obj != obj):
                    target_id = f"obj_{next(i for i, o in enumerate(self.json_data) if o.get('id') == value or o.get('name') == value)}"
                    self.graph.add_edge(obj_id, target_id, relation=key)
                    self.edge_labels[(obj_id, target_id)] = key
    
    def build_graph(self) -> None:
        """Build the knowledge graph based on detected data structure."""
        structure_type = self.detect_data_structure()
        print(f"Detected data structure: {structure_type}")
        
        if structure_type == 'patient_record':
            self.create_patient_record_graph()
        elif structure_type == 'policy':
            self.create_policy_graph()
        elif structure_type == 'data_dictionary':
            self.create_data_dictionary_graph()
        elif structure_type == 'graph_structure':
            self.create_graph_structure_graph()
        elif structure_type == 'simple_dict':
            self.create_simple_dict_graph()
        elif structure_type == 'object_list':
            self.create_object_list_graph()
        else:
            print(f"Unknown data structure: {structure_type}")
            print("Creating basic graph from JSON structure...")
            self.create_simple_dict_graph()
    
    def create_matplotlib_visualization(self, layout: str = 'spring', figsize: Tuple[int, int] = (15, 10), output_file: Optional[str] = None, input_file_path: Optional[str] = None, no_show: bool = False) -> None:
        """Create a matplotlib-based visualization of the knowledge graph."""
        plt.figure(figsize=figsize)
        
        # Choose layout
        if layout == 'spring':
            pos = nx.spring_layout(self.graph, k=3, iterations=50)
        elif layout == 'circular':
            pos = nx.circular_layout(self.graph)
        elif layout == 'hierarchical':
            pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
        else:
            pos = nx.spring_layout(self.graph)
        
        # Draw nodes
        for node in self.graph.nodes():
            nx.draw_networkx_nodes(
                self.graph, pos,
                nodelist=[node],
                node_color=self.node_colors.get(node, self.color_schemes['default']),
                node_size=self.node_sizes.get(node, 500),
                alpha=0.8
            )
        
        # Draw edges
        nx.draw_networkx_edges(
            self.graph, pos,
            edge_color='gray',
            alpha=0.6,
            width=1.5
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            self.graph, pos,
            labels=self.node_labels,
            font_size=8,
            font_weight='bold'
        )
        
        # Draw edge labels
        nx.draw_networkx_edge_labels(
            self.graph, pos,
            edge_labels=self.edge_labels,
            font_size=6
        )
        
        # Determine title based on data structure
        structure_type = self.detect_data_structure()
        if structure_type == 'patient_record':
            title = "Patient KG"
        elif structure_type == 'policy':
            title = "Policy KG"
        elif structure_type == 'data_dictionary':
            title = "Data Dictionary KG"
        else:
            title = "Knowledge Graph Visualization"
        
        plt.title(title, fontsize=16, fontweight='bold')
        plt.axis('off')
        
        # Create legend
        legend_elements = []
        for node_type, color in self.color_schemes.items():
            if any(self.graph.nodes[node].get('type') == node_type for node in self.graph.nodes()):
                legend_elements.append(mpatches.Patch(color=color, label=node_type.title()))
        
        if legend_elements:
            plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        
        # Save the plot
        if output_file:
            output_filename = f"{output_file}.png"
        else:
            output_filename = f"patient_kg_{layout}_{figsize[0]}x{figsize[1]}.png"
        
        # Determine output path
        if output_file:
            # If output_file is provided, use it as the full path
            output_path = output_filename
        elif input_file_path:
            # If no output_file but input_file_path is provided, use input file directory
            output_dir = os.path.dirname(os.path.abspath(input_file_path))
            output_path = os.path.join(output_dir, output_filename)
        else:
            # Default to current directory
            output_path = output_filename
            
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 Knowledge graph saved as: {output_path}")
        
        if not no_show:
            plt.show()
    
    def create_plotly_visualization(self, layout: str = 'spring', output_file: Optional[str] = None, input_file_path: Optional[str] = None) -> None:
        """Create an interactive Plotly visualization of the knowledge graph."""
        # Choose layout
        if layout == 'spring':
            pos = nx.spring_layout(self.graph, k=3, iterations=50)
        elif layout == 'circular':
            pos = nx.circular_layout(self.graph)
        else:
            pos = nx.spring_layout(self.graph)
        
        # Prepare data for Plotly
        edge_x = []
        edge_y = []
        edge_info = []
        
        for edge in self.graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            edge_data = self.graph.edges[edge]
            edge_info.append(f"Relation: {edge_data.get('relation', 'related')}")
        
        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='rgba(125,125,125,0.5)'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Prepare node data
        node_x = []
        node_y = []
        node_text = []
        node_hover = []
        node_colors = []
        node_sizes = []
        
        for node in self.graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            node_data = self.graph.nodes[node]
            node_text.append(self.node_labels.get(node, node))
            node_hover.append(f"<b>{node}</b><br>" + 
                            "<br>".join([f"{k}: {v}" for k, v in node_data.items() if k != 'type']))
            
            # Convert color to RGB
            color = self.node_colors.get(node, self.color_schemes['default'])
            if color.startswith('#'):
                rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                node_colors.append(f'rgb({rgb[0]},{rgb[1]},{rgb[2]})')
            else:
                node_colors.append('rgb(176,176,176)')
            
            node_sizes.append(self.node_sizes.get(node, 20))
        
        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            hovertext=node_hover,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='black')
            )
        )
        
        # Determine title based on data structure
        structure_type = self.detect_data_structure()
        if structure_type == 'patient_record':
            title = 'Patient KG'
        elif structure_type == 'policy':
            title = 'Policy KG'
        elif structure_type == 'data_dictionary':
            title = 'Data Dictionary KG'
        else:
            title = 'Interactive Knowledge Graph'
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title=title,
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           annotations=[ dict(
                               text=f"{title} - Hover over nodes for details",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor='left', yanchor='bottom',
                               font=dict(color="gray", size=12)
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           plot_bgcolor='white'
                       ))
        
        # Save the interactive plot
        if output_file:
            output_filename = f"{output_file}.html"
        else:
            output_filename = f"patient_kg_{layout}_interactive.html"
        
        # Determine output directory (same as input file if provided)
        if input_file_path:
            output_dir = os.path.dirname(os.path.abspath(input_file_path))
            output_path = os.path.join(output_dir, output_filename)
        else:
            output_path = output_filename
            
        fig.write_html(output_path)
        print(f"📊 Interactive knowledge graph saved as: {output_path}")
        
        fig.show()
    
    def print_graph_summary(self) -> None:
        """Print a summary of the knowledge graph."""
        print(f"\n📊 Knowledge Graph Summary:")
        print(f"   Total nodes: {self.graph.number_of_nodes()}")
        print(f"   Total edges: {self.graph.number_of_edges()}")
        
        # Node type breakdown
        node_types = {}
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print(f"\n📈 Node Types:")
        for node_type, count in sorted(node_types.items()):
            print(f"   {node_type}: {count}")
        
        # Edge type breakdown
        edge_types = {}
        for edge in self.graph.edges():
            edge_data = self.graph.edges[edge]
            edge_type = edge_data.get('relation', 'unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        print(f"\n🔗 Edge Types:")
        for edge_type, count in sorted(edge_types.items()):
            print(f"   {edge_type}: {count}")


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in file '{file_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading file '{file_path}': {e}")
        sys.exit(1)


def main():
    """Main function to run the patient knowledge graph visualizer."""
    parser = argparse.ArgumentParser(
        description="Create knowledge graphs from JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python patient_kg.py data.json
  python patient_kg.py data.json --layout circular --output static
  python patient_kg.py data.json --interactive --figsize 20 15
        """
    )
    
    parser.add_argument('input_file', help='Input JSON file path')
    parser.add_argument('--layout', choices=['spring', 'circular', 'hierarchical'], 
                       default='spring', help='Graph layout algorithm')
    parser.add_argument('--interactive', action='store_true', 
                       help='Create interactive Plotly visualization')
    parser.add_argument('--figsize', nargs=2, type=int, default=[15, 10],
                       help='Figure size for matplotlib (width height)')
    parser.add_argument('--output', choices=['static', 'interactive'], 
                       default='static', help='Output type')
    parser.add_argument('--output-file', type=str, 
                       help='Custom output filename (without extension)')
    parser.add_argument('--no-show', action='store_true',
                       help='Do not display the plot (only save to file)')
    
    args = parser.parse_args()
    
    # Load JSON data
    print(f"📁 Loading JSON data from: {args.input_file}")
    json_data = load_json_file(args.input_file)
    
    # Create visualizer
    print("🔧 Creating patient knowledge graph visualizer...")
    visualizer = PatientKGVisualizer(json_data)
    
    # Build graph
    print("🏗️  Building knowledge graph...")
    visualizer.build_graph()
    
    # Print summary
    visualizer.print_graph_summary()
    
    # Create visualization
    print("🎨 Creating visualization...")
    
    if args.interactive or args.output == 'interactive':
        visualizer.create_plotly_visualization(layout=args.layout, output_file=args.output_file, input_file_path=args.input_file)
    else:
        visualizer.create_matplotlib_visualization(
            layout=args.layout, 
            figsize=tuple(args.figsize),
            output_file=args.output_file,
            input_file_path=args.input_file,
            no_show=args.no_show
        )
    
    print("✅ Visualization complete!")


if __name__ == "__main__":
    main()