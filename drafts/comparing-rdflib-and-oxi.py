#%%
from rdflib import Graph, Literal
import sys
sys.path.append('..')
from namespaces import *
from tqdm import tqdm
from pyoxigraph import *

g = Graph(store = 'Oxigraph')
g.parse("../vrf-model.ttl", format="turtle")
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
s223 = Graph(store = 'Oxigraph')
s223.parse("../223p.ttl", format="turtle")
schema_data_graph  = s223 + g

def check_ns(node, ns):
    return str(ns) in str(node)


def get_class(node, data_graph = g, schema_graph = s223, schema_data_graph = schema_data_graph, ns = S223):
    # need schema and data graph 
    # schema_data_graph = schema_graph + data_graph 
    # get relevant subgraph
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
        if not (check_ns(s, EX) and check_ns(o, EX)):
            continue
        if check_ns(p, ns):
            s_class = get_class(s)
            o_class = get_class(o)
            new_graph.add((s_class, p, o_class))
            # groups[str(s)].append(str(o))
    return new_graph
make_groups()
# %%
# on SDH model 
store = Store()
dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")
store.load(path = "../vrf-model.ttl", format = RdfFormat.TURTLE, to_graph=dg)
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
store.load(path = "../223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)

g = Graph()
g.parse("223p.ttl", format="turtle")
prefixes = get_prefixes(g)

def get_class(node, ns = S223):
    
    query = f"""
    {prefixes}
    # PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class WHERE {{
        {str(node)} a ?class . 
        FILTER NOT EXISTS {{
            {str(node)} a ?subclass .
            ?subclass rdfs:subClassOf ?class .
        }}
        FILTER(STRSTARTS(STR(?class), str(s223:)))
    }} """
    r = store.query(query, use_default_graph_as_union=True)
    return r

def make_groups(store, ns = S223, start_node = None):
    new_graph = Graph()
    groups = {}
    length = len(g)
    i = 0
    for quad in tqdm(store):
        if not check_ns(quad.subject, EX):
            continue
        if not check_ns(quad.object, EX):
            continue
        if check_ns(quad.predicate, ns):
            s_class = get_class(quad.subject)
            try:
              o_class = get_class(quad.object)
            except Exception as e:
              print(e)
              print(quad.object)
              # continue
              return
    return new_graph
make_groups(store)
#%%

# Conclusion, oxygraph can make a big difference