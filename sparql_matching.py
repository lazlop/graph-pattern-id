# %%
from dataclasses import dataclass
from pyoxigraph import * 
from namespaces import *
from rdflib import Graph, URIRef
from collections import defaultdict
from itertools import combinations
import pandas as pd
from figuring_out_sparql_tables import find_sets
from IPython.display import display
# to query with pyoxigraph I must use the default graph as union or set the efault graph

# store = Store()
# dg = NamedNode("urn:data-graph")
# sg = NamedNode("urn:schema-graph")
# # store.load(path = "vrf-model.ttl", format = RdfFormat.TURTLE, to_graph=dg)
# store.load(path = "test-graph.ttl", format = RdfFormat.TURTLE, to_graph=dg)
# EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
# store.load(path = "223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)
# dg = NamedNode("urn:data-graph")
# sg = NamedNode("urn:schema-graph")
g = Graph(store = 'Oxigraph')
# # g.parse("vrf-model.ttl", format="turtle")
g.parse("test-graph.ttl", format="turtle")
# EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
EX = Namespace("urn:example#")
# s223 = Graph(store = 'Oxigraph')
# s223.parse("223p.ttl", format="turtle")
# schema_data_graph  = s223 + g
prefixes = get_prefixes(g)
store = Store()
dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")
# store.load(path = "vrf-model.ttl", format = RdfFormat.TURTLE, to_graph=dg)
store.load(path = "test-graph5.ttl", format = RdfFormat.TURTLE, to_graph=dg)
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
store.load(path = "223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)

def get_local_name(node):
    node = str(node).replace('<', '').replace('>', '')
    if '#' in node:
        return node.rpartition('#')[-1]
    else:
        return node.rpartition('/')[-1]
    
def get_prefixed_name(node):
    # TODO: Make this function as intended
    node = str(node).replace('<', '').replace('>', '')
    if '#' in node:
        return f"s223:{node.rpartition('#')[-1]}"
    else:
        return f"s223:{node.rpartition('/')[-1]}"
# may need to make my own triple dataclass
@dataclass(frozen=True)
class Triple():
    s:str
    p:str
    o:str
    
    def __str__(self):
        return f"{self.s} {self.p} {self.o}"

def get_class(node, store = store, prefixes = prefixes, ns = S223):
    
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
    classes = list(store.query(query, use_default_graph_as_union=True))
    if len(classes) == 0:
        return None
    return classes[0]['class'].value

query = ""
def walk_graph_sequentially(store, graph_name = dg, start_node=None, max_depth=None):
    """
    Sequentially walk an RDF graph using depth-first traversal.
    
    Args:
        graph: RDF graph to traverse (rdflib.Graph or pyoxigraph store)
        start_node: Starting node for traversal (if None, starts with first subject found)
        max_depth: Maximum depth to traverse (if None, no limit)
    
    Returns:
        List of tuples representing the traversal path: [(subject, predicate, object), ...]
    """
    visited = set()
    path = []
    groups = []
    query = ""

    def get_all_triples(store):
            # pyoxigraph store
            return list(store.quads_for_pattern(None, None, None, graph_name))
    
    def get_neighbors(node, store):
        """Get all neighboring nodes (both as subject and object)"""
        neighbors = []
        # pyoxigraph store
        for quad in store.quads_for_pattern(None, None, node, graph_name):
            s, p, o = quad.subject, quad.predicate, quad.object
            neighbors.append((s, p, o, 'incoming')) 

        # literals can't be subjects
        if isinstance(node, Literal):
            return neighbors
        
        for quad in store.quads_for_pattern(node, None, None, graph_name):
            s, p, o = quad.subject, quad.predicate, quad.object
            neighbors.append((s, p, o, 'outgoing'))
        return neighbors
    
    def dfs_walk(current_node, depth=0):
        """Depth-first search traversal"""
        if max_depth is not None and depth > max_depth:
            return
        
        if current_node in visited:
            return
        visited.add(current_node)
        print("node: ", current_node)
        print("class: ", get_class(current_node, store, prefixes, ns = EX))
        
        # Get all neighbors of current node
        neighbors = get_neighbors(current_node, store)
        
        # First, add all triples involving this node to the path
        for s, p, o, direction in neighbors:
            triple_tuple = (s, p, o)
            if triple_tuple not in [t[:3] for t in path]:  # Avoid duplicate triples
                path.append((s, p, o, direction, depth))

                # add triple to group
                object = get_class(str(o))
                if object is None:
                    continue
                groups.append(
                    (Triple(str(get_class(s)), str(p), str(get_class(o))),
                    Triple(str(s), str(p), str(o))
                    )
                )

                p = PatternQuery(groups)
                print('WHERE')
                global query 
                query = p.query
                print(p.where)
                # print('QUERYING FOR: ', current_node, "ON PATH: ", path)
                print('RESULTS')
                res = store.query(p.query, default_graph = [dg])
                df = pd.DataFrame(list(res), columns = res.variables).map(get_local_name)
                display(df)
                # print(groups)

                # Continue traversal to connected nodes
                if direction == 'outgoing' and o not in visited:
                    dfs_walk(o, depth + 1)
                elif direction == 'incoming' and s not in visited:
                    dfs_walk(s, depth + 1)

        # # Then, recursively visit all unvisited connected nodes
        # for s, p, o, direction in neighbors:
        #     if direction == 'outgoing' and o not in visited:
        #         dfs_walk(o, depth + 1)
        #     elif direction == 'incoming' and s not in visited:
        #         dfs_walk(s, depth + 1)
    
    # Get starting node if not provided
    if start_node is None:
        all_triples = get_all_triples(store)
        if all_triples:
            start_node = all_triples[0][0]  # Use first subject as starting point
        else:
            return []  # Empty graph
    
    # Start the traversal
    dfs_walk(start_node)
    
    return path
    
class PatternQuery:
    def __init__(self, triples, graph = g):
        self.triples = triples
        # self.graph = graph
        # self.prefixes = get_prefixes(graph)
        self.query_dict = self.make_var_names(triples)
        self.filters = self.add_filters(self.query_dict)
        self.where = self.add_where(self.query_dict)
        self.query = self.get_query()
    
    def add_filters(self, triples):
        filter_lst = []
        # anything of the same class should not equal another var of the same class
        filter_dict = defaultdict(set)
        for class_triple, var_triple in triples:
            filter_dict[class_triple.s].add(var_triple.s)
            filter_dict[class_triple.o].add(var_triple.o)
        for klass, var_list in filter_dict.items():
            if len(var_list) == 1:
                continue
            for var_1, var_2 in combinations(var_list,2):
                filter_lst.append(f"FILTER (?{var_1} != ?{var_2}) .")
        
        return "\n".join(filter_lst) 
    def make_var_names(self,triples):
        # makes a dictionary with triples of classes to triples with var names
        """
        Makes a dictionary with triples of classes to triples with var names
        :param triples: a list of tuples, where each tuple contains a triple of classes and a triple of variables
        :return: a list of tuples, where each tuple contains a triple of classes and a triple of variables with var names
        """
        counter = {}
        query_triples = []
        for class_triple, var_triple in triples:
            subject = get_local_name(var_triple.s)
            object = get_local_name(var_triple.o)
            # have to remove angle brackets from predicate
            if class_triple.p.startswith('<'):
                p_var = class_triple.p.split('<')[1].split('>')[0]
            else:
                p_var = class_triple.p
            query_triples.append((class_triple,Triple(subject,p_var,object)))
        return query_triples
    # query fragments can be list, then list can be continuously concatenated with fragments. fragments can be joined by '\n'
    def add_where(self,query_triples):
        where = []
        for klass, var in query_triples:
            where.append(f"?{var.s} a {convert_to_prefixed(klass.s,g)} .")
            where.append(f"?{var.s} {convert_to_prefixed(URIRef(var.p),g)} ?{var.o} .")
            where.append(f"?{var.o} a {convert_to_prefixed(klass.o, g)} .")
        return '\n'.join(where)
    
    def get_query(self):
        # may need to add prefixes
        query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {self.where}\n{self.filters} }} """
        return query

path = walk_graph_sequentially(store)
# %%
sets = find_sets(query, store)
display(sets)

# %%
#Trying just going over the whole graph, no depth first search 

def check_ns(node, ns = S223):
    # would have been better to do with sparql
    # have to get rid of starting bracket
    # hardcoding 223 for now 
    return get_local_name(node) == str(node).replace(str(ns),'').replace('<','').replace('>','')


groups = []
for quad in list(store.quads_for_pattern(None, None, None, dg)):
    print(quad)
    if not check_ns(quad.predicate):
        print("predicate not in 223")
        continue
    s_class = get_class(str(quad.subject))
    if s_class is None:
        continue
    o_class = get_class(str(quad.object))
    if o_class is None:
        continue
    groups.append(
            (Triple(str(s_class), str(quad.predicate), str(o_class)),
            Triple(str(quad.subject), str(quad.predicate), str(quad.object))
            )
        )
print(groups)
p = PatternQuery(groups)
print('WHERE')
query = p.query
print(p.where)
# print('QUERYING FOR: ', current_node, "ON PATH: ", path)
print('RESULTS')
res = store.query(p.query, default_graph = [dg])
df = pd.DataFrame(list(res), columns = res.variables).map(get_local_name)
display(df)
sets = find_sets(query, store)
display(sets)

def get_group_relations(groups, sets):
    # can double check relation between groups and compose a new_graph
    new_graph_triples = []
    for class_triple, triple in groups:
        for s_set in sets:
            if isinstance(s_set, tuple):
                s_set = list(s_set)
            else:
                s_set = [s_set]
            if Variable(triple.s) in s_set:
                for o_set in sets:
                    if isinstance(o_set, tuple):
                        o_set = list(o_set)
                    else:
                        o_set = [o_set]
                    if Variable(triple.o) in o_set:
                        new_graph_triples.append((
                            Triple(class_triple.s, triple.p, class_triple.o),
                            Triple(s_set, triple.p, o_set))
                        )
    return new_graph_triples
temp = get_group_relations(groups = p.query_dict, sets = sets)

def group_serialization(group):
    return '_'.join(str(var).replace('?','x') for var in group)

def create_new_graph(triples):
    # create a new graph with the triples
    # serialize groups 
    group_dict = {}
    group_triples = []
    for class_triple, triple in triples:
        s = group_serialization(triple.s)
        o = group_serialization(triple.o)
        group_dict[s] = triple.s
        group_dict[o] = triple.o
        store.add(Quad(NamedNode(EX[s]), NamedNode(triple.p), NamedNode(EX[o]), NamedNode(EX)))
        store.add(Quad(NamedNode(EX[s]), NamedNode(A), NamedNode(class_triple.s), NamedNode(EX)))
        store.add(Quad(NamedNode(EX[o]), NamedNode(A), NamedNode(class_triple.o), NamedNode(EX)))
    return group_dict

# %%
dct = create_new_graph(temp)
display(dct)

groups = []
for quad in list(store.quads_for_pattern(None, None, None, NamedNode(EX))):
    print(quad)
    if not check_ns(quad.predicate):
        print("predicate not in 223")
        continue
    s_class = get_class(str(quad.subject))
    if s_class is None:
        continue
    o_class = get_class(str(quad.object))
    if o_class is None:
        continue
    groups.append(
            (Triple(str(s_class), str(quad.predicate), str(o_class)),
            Triple(str(quad.subject), str(quad.predicate), str(quad.object))
            )
        )
# %%
p = PatternQuery(groups)
res = store.query(p.query, default_graph = [NamedNode(EX)])
df = pd.DataFrame(list(res), columns = res.variables).map(get_local_name)
display(df)
sets = find_sets(p.query, store)
display(sets)
# %%
