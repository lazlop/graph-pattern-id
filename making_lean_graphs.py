#%%
"""
Maybe borrow ideas of lean graphs and then create groups based on class and connected class. 
Lean just means that there are no redundant triples in a graph. 
For this case it may be better just to define the relations of interest and maybe the ontologies used for classes. 
Could also specifically be interested in the classes. """

from rdflib import Graph, BNode, Literal, Namespace, RDF, URIRef
import pandas as pd
from namespaces import * 
from tqdm import tqdm

EX = Namespace("http://data.ashrae.org/standard223/data/lbnl-example-2#")
s223 = Graph(store = 'Oxigraph')
s223.parse("223p.ttl", format="turtle")

g = Graph(store = 'Oxigraph')
g.parse("vrf-model.ttl", format="turtle")

# %%
# rules 
# only include the most specific class (could also just consider the set of classes, but this is a shortcut for now)
# only considers the desired relations
# Take 



def check_ns(node, ns):
    return str(ns) in str(node)

def get_class(node, data_graph = g, schema_graph = s223, ns = S223):
    # need schema and data graph 
    # schema_data_graph = schema_graph + data_graph 
    # get relevant subgraph
    class_graph = data_graph.query(f"""CONSTRUCT {{<{node}> a ?class . }} 
                                   WHERE {{ <{node}> a ?class .
                                   FILTER(STRSTARTS(STR(?class), "{str(ns)}")) 
                                   }} """).graph
    schema_data_graph = schema_graph + class_graph
    query = f"""
    SELECT DISTINCT ?class WHERE {{
        <{node}> a ?class . 
        FILTER NOT EXISTS {{
            <{node}>  a ?subclass .
            ?subclass rdfs:subClassOf ?class .
        }}
        FILTER(STRSTARTS(STR(?class), "{str(ns)}"))
    }} """
    r = schema_data_graph.query(query)
    if len(r.bindings) == 0:
        get_label = f"""
        SELECT ?label WHERE {{
            <{node}> rdfs:label ?label .
        }}"""
        r = (data_graph + schema_graph).query(get_label)
        if len(r.bindings) > 0:
            print('didnt find correct class')
            print(r.bindings[0]['label'])
            return r.bindings[0]['label']
        return Literal(None)
    # print(r.bindings[0]['class'])
    return r.bindings[0]['class']
def make_groups(g = g, ns = S223, start_node = None):
    new_graph = Graph()
    groups = {}
    length = len(g)
    i = 0
    for s, p, o in tqdm(g):
        if check_ns(p, ns):
            s_class = get_class(s)
            o_class = get_class(o)
            new_graph.add((s_class, p, o_class))
            # groups[str(s)].append(str(o))
    return new_graph
    
# %%
make_groups()
# %%
