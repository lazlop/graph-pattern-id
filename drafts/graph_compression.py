
# %% 
""" 
Compressing a graph by putting nodes into groups and doing group-to-group relationships. 
Going to have 2 or 3 groups with 1-to-1 relationships, 1-to-all relationships, and all-to-all relationships

Maybe not 1-to-1, 1-to-all, all-to-all, but creating groups within groups. 
Everything maintains their own identity but the groups are super imposed. 

Lets start just with cnx and see what happens, or maybe try a tree structure containment? 

If groups contain groups, everything can be 1-to-all (or each to all) 
this each to all doesn't seem to be very helpful, since it will just replicate the tree structure 
and doesn't bring together separate branches of tree
it won't "fold" the tree, which I would like to do. 

Maybe I try and create groups by walking the graph.
Start with all things of a certain type in a big group. 
Walk 1 connection away. All things connected to another thing of the same type are in a group. 
Lets say all valves are connected to a junction or a heating coil - i'd have two groups.
buildings can be fully connected. 
I do this process again and again, keeping track of all groups. 
groups end where the connection types diverge. 
can choose what relationships are important to consider for making my groups.
Just cnx and type, or cnx and type and property maybe. 

Not sure if I should care about cardinality. Is a junction connecting to 3 things meaningfully different than one connecting to 5 things. 
This process is for visualizing the building and as a helpful view for creating queries, it isn't for speeding up query runtime

This is not working well ... 

Maybe borrow ideas of lean graphs and then create groups based on class and connected class. 
Lean just means that there are no redundant triples in a graph. 
For this case it may be better just to define the relations of interest and maybe the ontologies used for classes. 
Could also specifically be interested in the classes. 
"""
from rdflib import Graph, BNode, Literal, Namespace, RDF, URIRef
import pandas as pd
# %%
g = Graph(store = 'Oxigraph')
# %%
# function to create test graph 
EX = Namespace("urn:example#")
def create_test_graph():
    g = Graph(store = 'Oxigraph')
    g.parse("test-graph.ttl")
    return g

import io
import pydot
from IPython.display import display, Image
from rdflib.tools.rdf2dot import rdf2dot

def visualize(g, show_type = False):
    stream = io.StringIO()
    if show_type:
        g_vis = g
    else:
        g_vis = g.query("CONSTRUCT {?s ?p ?o} WHERE { ?s ?p ?o . FILTER (?p != rdf:type) }").graph
    rdf2dot(g_vis, stream)
    dg = pydot.graph_from_dot_data(stream.getvalue())[0]
    png = dg.create_png()
    # png = dg.write_png(f'{name}.png')
    display(Image(png))

g = create_test_graph()
visualize(g)
# %%

def compress_graph(g):
    # groups with dictionaries of types and nodes
    groups = {}
    #groups of each to all
    eta = {}
    relations = {}
    g2 = Graph()
    for s, p, o in g:
        if p == RDF.type:
            # groups[str(o)].append(str(s))
            groups[str(s)] = str(o)
            g2.add((o, EX.hasMember, s))

    for s, p, o in g:
        if p != RDF.type:
            if str(p) not in relations:
                rset = set()
                relations[str(p)] = rset
            else:
                rset = relations[str(p)]
            rset.add((groups[str(s)],groups[str(o)]))
            g2.add((URIRef(groups[str(s)]), URIRef(str(p)), URIRef(groups[str(o)])))
        
    return groups,relations, g2
groups, relations, g2 = compress_graph(g)

print(relations)
# %%
visualize(g2)
# %%
query = """
SELECT ?s ?o WHERE {
    ?g1 ex:hasMember ?s .
    ?g2 ex:hasMember ?o .
    ?s ex:cnx ?o .
}
"""
results = (g2 + g).query(query)

# %%
df = pd.DataFrame(results.bindings)
display(df)
# %%
visualize(g2+g)
# %%
import rdflib
from collections import defaultdict

def group_similar_structures(graph, start_type):
    """
    Group similar structures in an RDF graph.
    
    Args:
        graph: An rdflib.Graph instance
        start_type: The RDF type to start grouping from (as a URIRef)
    
    Returns:
        Dictionary of groups, where keys are pattern signatures and values are lists of nodes
    """
    # Find all instances of the start type
    instances = list(graph.subjects(rdflib.RDF.type, start_type))
    
    # Initialize groups
    groups = defaultdict(list)
    
    # Process each instance
    for instance in instances:
        # Get the pattern signature for this instance
        signature = get_connection_signature(graph, instance)
        groups[signature].append(instance)
    
    return groups

def get_connection_signature(graph, node, depth=10, visited=None):
    """
    Generate a signature for the node based on its connections.
    
    Args:
        graph: The RDF graph
        node: The node to analyze
        depth: How many connections to walk (default: 1)
        visited: Set of visited nodes (to avoid cycles)
    
    Returns:
        A tuple representing the connection pattern
    """
    if visited is None:
        visited = set()
    
    if node in visited or depth <= 0:
        return ()
    
    visited.add(node)
    
    # Get all predicates and objects where this node is the subject
    outgoing = []
    for pred, obj in graph.predicate_objects(node):
        # Get the type of the object if it's a blank node or URI
        obj_type = None
        if isinstance(obj, (rdflib.URIRef, rdflib.BNode)):
            types = list(graph.objects(obj, rdflib.RDF.type))
            obj_type = types[0] if types else "Unknown"
        
        # Add to outgoing connections
        outgoing.append((pred, obj_type))
    
    # Sort for consistent ordering
    outgoing.sort()
    
    # Create a signature tuple
    signature = tuple(outgoing)
    
    # If we need to go deeper, extend the signature
    if depth > 1:
        extended = []
        for _, obj in graph.predicate_objects(node):
            if isinstance(obj, (rdflib.URIRef, rdflib.BNode)) and obj not in visited:
                sub_sig = get_connection_signature(graph, obj, depth-1, visited)
                extended.append(sub_sig)
        
        # Sort and add to signature
        extended.sort()
        signature = signature + tuple(extended)
    
    return signature

def print_groups(groups, graph):
    """Print the groups in a readable format"""
    for i, (signature, nodes) in enumerate(groups.items()):
        print(f"Group {i+1} (Size: {len(nodes)}):")
        print("  Pattern:", signature_to_readable(signature, graph))
        print("  Members:")
        for node in nodes[:5]:  # Show first 5 members
            print(f"    - {node}")
        if len(nodes) > 5:
            print(f"    ... and {len(nodes) - 5} more")
        print()

def signature_to_readable(signature, graph):
    """Convert a signature tuple to a more readable format"""
    result = []
    for pred, obj_type in signature:
        pred_name = graph.namespace_manager.qname(pred) if isinstance(pred, rdflib.URIRef) else pred
        obj_name = graph.namespace_manager.qname(obj_type) if isinstance(obj_type, rdflib.URIRef) else obj_type
        result.append(f"{pred_name} → {obj_name}")
    return ", ".join(result)

import rdflib
from collections import defaultdict

def group_similar_structures(graph, start_type, depth=1):
    """
    Group similar structures in an RDF graph.
    
    Args:
        graph: An rdflib.Graph instance
        start_type: The RDF type to start grouping from (as a URIRef)
        depth: How many connections to walk
    
    Returns:
        Dictionary of groups, where keys are pattern signatures and values are lists of nodes
    """
    # Find all instances of the start type
    instances = list(graph.subjects(rdflib.RDF.type, start_type))
    
    # Initialize groups
    groups = defaultdict(list)
    
    # Process each instance
    for instance in instances:
        # Get the pattern signature for this instance
        signature = get_connection_signature(graph, instance, depth=depth)
        # Use a string representation of the signature as the key
        signature_key = str(signature)
        groups[signature_key].append(instance)
    
    return groups

def get_connection_signature(graph, node, depth=1, visited=None):
    """
    Generate a signature for the node based on its connections.
    
    Args:
        graph: The RDF graph
        node: The node to analyze
        depth: How many connections to walk (default: 1)
        visited: Set of visited nodes (to avoid cycles)
    
    Returns:
        A tuple representing the connection pattern
    """
    if visited is None:
        visited = set()
    
    if node in visited or depth <= 0:
        return ()
    
    visited.add(node)
    
    # Get all predicates and objects where this node is the subject
    outgoing = []
    for pred, obj in graph.predicate_objects(node):
        # Skip rdf:type predicates to avoid redundancy
        if pred == rdflib.RDF.type:
            continue
            
        # Get the type of the object if it's a blank node or URI
        obj_type = None
        if isinstance(obj, (rdflib.URIRef, rdflib.BNode)):
            types = list(graph.objects(obj, rdflib.RDF.type))
            obj_type = types[0] if types else "Unknown"
            
            # If we need to go deeper, get the sub-signature
            if depth > 1 and obj not in visited:
                sub_sig = get_connection_signature(graph, obj, depth-1, visited.copy())
                outgoing.append((pred, obj_type, sub_sig))
            else:
                outgoing.append((pred, obj_type))
        else:
            # For literals, just store the predicate and a marker for literal
            outgoing.append((pred, "Literal"))
    
    # Sort for consistent ordering
    outgoing.sort()
    
    return tuple(outgoing)

def print_groups(groups, graph):
    """Print the groups in a readable format"""
    for i, (signature_key, nodes) in enumerate(groups.items()):
        print(f"Group {i+1} (Size: {len(nodes)}):")
        print("  Pattern:")
        # Convert the string representation back to a structured form for display
        signature = eval(signature_key)
        print_signature(signature, graph, indent=2)
        print("  Members:")
        for node in nodes[:5]:  # Show first 5 members
            print(f"    - {node}")
        if len(nodes) > 5:
            print(f"    ... and {len(nodes) - 5} more")
        print()

def print_signature(signature, graph, indent=0):
    """Print a signature in a readable hierarchical format"""
    indent_str = " " * indent
    for item in signature:
        if len(item) == 2:
            pred, obj_type = item
            pred_name = graph.namespace_manager.qname(pred) if isinstance(pred, rdflib.URIRef) else pred
            obj_name = graph.namespace_manager.qname(obj_type) if isinstance(obj_type, rdflib.URIRef) else obj_type
            print(f"{indent_str}- {pred_name} → {obj_name}")
        elif len(item) == 3:
            pred, obj_type, sub_sig = item
            pred_name = graph.namespace_manager.qname(pred) if isinstance(pred, rdflib.URIRef) else pred
            obj_name = graph.namespace_manager.qname(obj_type) if isinstance(obj_type, rdflib.URIRef) else obj_type
            print(f"{indent_str}- {pred_name} → {obj_name}")
            if sub_sig:
                print(f"{indent_str}  Connected to:")
                print_signature(sub_sig, graph, indent=indent+4)


g = rdflib.Graph()
g.parse("test-graph.ttl", format="turtle")
    
# Define the type you want to start with
valve_type = EX["1"]
    
# Get groups
valve_groups = group_similar_structures(g, valve_type,depth=5)

# Print the groups
print_groups(valve_groups, g)

# %%
S223 = Namespace("http://data.ashrae.org/standard223#")

g.parse("reasoned_build.ttl", format="turtle")
    
# Define the type you want to start with
valve_type = S223['FanPoweredTerminal']
    
# Get groups
valve_groups = group_similar_structures(g, valve_type,depth=2)

# Print the groups
print_groups(valve_groups, g)
# %%
