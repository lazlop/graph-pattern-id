#%%
from pyoxigraph import *
from namespaces import *
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from IPython.display import display

store = Store()
dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")
# store.load(path = "vrf-model.ttl", format = RdfFormat.TURTLE, to_graph=dg)
store.load(path = "test-graph.ttl", format = RdfFormat.TURTLE, to_graph=dg)
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
store.load(path = "223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)

query = """PREFIX s223: <http://data.ashrae.org/standard223#>
PREFIX unit: <http://qudt.org/vocab/unit/>
PREFIX ex: <urn:example#>
SELECT DISTINCT ?1_1 WHERE { ?1_2 a s223:Branch .
?1_2 s223:cnx ?2_2 .
?2_2 a s223:Leaf .
?0_0 a s223:Root .
?0_0 s223:cnx ?1_2 .
?1_2 a s223:Branch .
?0_0 a s223:Root .
?0_0 s223:cnx ?1_1 .
?1_1 a s223:Branch .
?0_0 a s223:Root .
?0_0 s223:cnx ?1_0 .
?1_0 a s223:Branch .
?1_2 a s223:Branch .
?1_2 s223:cnx ?2_1 .
?2_1 a s223:Leaf .
?1_2 a s223:Branch .
?1_2 s223:cnx ?2_0 .
?2_0 a s223:Leaf .
FILTER (?1_2 != ?1_1) .
FILTER (?1_2 != ?1_0) .
FILTER (?1_1 != ?1_0) .
FILTER (?2_0 != ?2_1) .
FILTER (?2_0 != ?2_2) .
FILTER (?2_1 != ?2_2) . } """

r = store.query(query, use_default_graph_as_union=True)

def get_local_name(node):
    node = str(node).replace('<', '').replace('>', '')
    if '#' in node:
        return node.rpartition('#')[-1]
    else:
        return node.rpartition('/')[-1]
# %%
df = pd.DataFrame(list(r), columns = r.variables).map(get_local_name)
display(df)
# %%
"""
group 1 is 0_0
0_0,  

# if columns are just shuffling values between them 

for each row 
len(col) = len(unique(values))
for all rows 
len(col) = len(unique(values))

"""
# check if any two columns have the same value counts 
#%%
import pandas as pd
import numpy as np
from itertools import combinations

def find_overlap_columns(df):
    """
    Check if any two columns in a DataFrame have the same value counts.
    
    Parameters:
    df (pandas.DataFrame): The DataFrame to check
    
    Returns:
    list: Pairs of column names that have identical value counts
    """
    result = []
    
    # Get all possible pairs of columns
    column_pairs = list(combinations(df.columns, 2))
    
    for col1, col2 in column_pairs:
        # Get value counts for both columns
        counts1 = df[col1].value_counts().sort_index()
        counts2 = df[col2].value_counts().sort_index()
        
        # Check if they have the same indices (values)
        if not counts1.index.equals(counts2.index):
            continue
            
        # Check if the counts are the same
        if not counts1.equals(counts2):
            continue
        
        # check if the columns are identical 
        if np.array_equal(df[col1], df[col2]):
            print('columns are identical')
            continue 

        result.append((col1, col2))
    # get unpaired columns
    unpaired = []
    for col in df.columns:
        if col not in [c1 for c1, c2 in result] and col not in [c2 for c1, c2 in result]:
            unpaired.append(col)

    return result, unpaired
#%%
# same_counts, _ = find_overlap_columns(df)
# for col1, col2 in same_counts:
#     print(f"{col1} and {col2}")
#     print(f"Value counts for {col1}: {df[col1].value_counts().to_dict()}")
#     print(f"Value counts for {col2}: {df[col2].value_counts().to_dict()}")


# %%

def find_cycles(pairs):
    # Create a directed graph
    G = nx.Graph()
    
    # Add edges from the tuple pairs
    G.add_edges_from(pairs)
    
    # Find simple cycles in the graph
    cycles = list(nx.simple_cycles(G))
    
    return cycles

def find_sets_from_pairs(pairs):
    cycles = find_cycles(pairs)
    # Convert to tuples for hashability
    pair_tuples = [tuple(lst) for lst in pairs]
    # Create a set
    check_set = set(pair_tuples)
    
    for cycle in cycles:
        cycle_tuple_set = set(combinations(cycle, 2))
        intersection = check_set.intersection(cycle_tuple_set)
        if intersection:
            check_set -= intersection
    
    groups = list(check_set)
    return groups + [tuple(cycle) for cycle in cycles]

def find_sets(query, store):
    df = pd.DataFrame(list(store.query(query, use_default_graph_as_union=True)), columns = store.query(query, use_default_graph_as_union=True).variables).map(get_local_name)
    pairs, unpaired = find_overlap_columns(df)
    groups = find_sets_from_pairs(pairs)
    return groups + unpaired


# lets not forget about the final individual node, which is its own set. 
#%%
find_sets(query, store)
# %%
# check test graph
import io
import pydot
from IPython.display import display, Image
from rdflib.tools.rdf2dot import rdf2dot
from rdflib import Graph

g = Graph()
g.parse("test-graph5.ttl")
g2 = g.query("CONSTRUCT {?s ?p ?o} WHERE { ?s ?p ?o . FILTER (?p != rdf:type) }").graph
stream = io.StringIO()
rdf2dot(g2, stream)
dg = pydot.graph_from_dot_data(stream.getvalue())[0]
dg.write_png("test.png")
# %%
