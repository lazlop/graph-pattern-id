import networkx as nx
import matplotlib.pyplot as plt
import re
from typing import List, Union, Optional, Tuple, Dict, Any

def visualize_triples(triples_data: List[str], 
                      figsize: Tuple[int, int] = (12, 10),
                      node_size: int = 2000,
                      node_color: str = "lightblue",
                      edge_color: str = "gray",
                      font_size: int = 10,
                      title: str = "Graph of Triples with Connection Relationships",
                      save_path: Optional[str] = None) -> plt.Figure:
    """
    Visualize RDF-like triples as a directed graph.
    
    Args:
        triples_data: List of triple strings in the format "Triple(s=[...], p='...', o=[...])"
        figsize: Figure size as (width, height) in inches
        node_size: Size of nodes in the graph
        node_color: Color of nodes
        edge_color: Color of edges
        font_size: Size of node labels
        title: Title of the graph
        save_path: Path to save the figure (if None, figure will be shown but not saved)
        
    Returns:
        matplotlib Figure object
    """
    # Create a directed graph
    G = nx.DiGraph()

    # Process each triple
    for triple in triples_data:
        # Extract subjects and objects
        G.add_edge(triple.s, triple.o)

    # Create a more organized layout
    pos = nx.spring_layout(G, seed=42)

    # Create figure
    fig = plt.figure(figsize=figsize)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_color, alpha=0.8)

    # Draw edges with arrows
    nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.7, edge_color=edge_color, 
                           connectionstyle='arc3,rad=0.1', arrowsize=15)

    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=font_size, font_family="sans-serif")

    # Add a title
    plt.title(title, fontsize=16)

    # Remove axis
    plt.axis("off")
    plt.tight_layout()
    
    # Save or show the figure
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
    
    return fig

# Example usage (commented out)
# if __name__ == "__main__":
#     triples_data = [
#         "Triple(s=[<Variable value=xroot>, <Variable value=xroot2>], p='http://data.ashrae.org/standard223#cnx', o=[<Variable value=xloop1_xloop2>, <Variable value=xloop3>])",
#         # ... other triples
#     ]
#     fig = visualize_triples(triples_data)
#     plt.show()