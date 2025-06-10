# %%
from dataclasses import dataclass
from pyoxigraph import * 
from namespaces import *
from rdflib import Graph

dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")

def get_local_name(node):
    node = str(node).replace('<', '').replace('>', '')
    if '#' in node:
        return node.rpartition('#')[-1]
    else:
        return node.rpartition('/')[-1]
    
# may need to make my own triple dataclass
@dataclass(frozen=True)
class Triple():
    s:str
    p:str
    o:str
    
    def __str__(self):
        return f"{self.s} {self.p} {self.o}"

def get_class(node, store, prefixes, ns = S223):
    
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
        print(current_node)
        visited.add(current_node)
        
        # Get all neighbors of current node
        neighbors = get_neighbors(current_node, store)
        
        # First, add all triples involving this node to the path
        for s, p, o, direction in neighbors:
            triple_tuple = (s, p, o)
            if triple_tuple not in [t[:3] for t in path]:  # Avoid duplicate triples
                path.append((s, p, o, direction, depth))
        
        # Then, recursively visit all unvisited connected nodes
        for s, p, o, direction in neighbors:
            if direction == 'outgoing' and o not in visited:
                dfs_walk(o, depth + 1)
            elif direction == 'incoming' and s not in visited:
                dfs_walk(s, depth + 1)
    
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

def walk_graph_by_groups(store, graph_name = dg):
    """
    Walk the graph and group nodes based on structural patterns.
    
    Args:
        graph: RDF graph to process
    
    Returns:
        List of groups, where each group contains related triples
    """
    groups = []
    remaining_triples = set()
    
    all_quads = store.quads_for_pattern(None, None, None, graph_name)
    all_triples = [(quad.subject, quad.predicate, quad.object) for quad in all_quads]
    
    remaining_triples.update(all_triples)
    
    while remaining_triples:
        # Start with an arbitrary triple
        current_triple = next(iter(remaining_triples))
        current_group = set()
        to_process = [current_triple]
        
        while to_process:
            triple = to_process.pop()
            if triple in remaining_triples:
                current_group.add(triple)
                remaining_triples.remove(triple)
                
                # Find connected triples
                s, p, o = triple
                for other_triple in list(remaining_triples):
                    other_s, other_p, other_o = other_triple
                    
                    # Check if triples are connected (share subject or object)
                    if (s == other_s or s == other_o or 
                        o == other_s or o == other_o):
                        to_process.append(other_triple)
        
        if current_group:
            groups.append(list(current_group))
    
    return groups
    
class PatternQuery:
    def __init__(self, triples, graph):
        self.triples = triples
        self.graph = graph
        self.prefixes = get_prefixes(graph)
        self.query_dict, self.filters = self.make_var_names(triples)
        self.where = self.add_where(self.query_dict)
        self.query = self.get_query()


    def add_filters(self, counter):
        filter_lst = []
        for klass, num in counter.items():
            if num < 1:
                continue 
            for n in range(1,num):
                for n_i in range(1, n):
                    filter_lst.append(f"FILTER (?{klass}{n_i} != ?{klass}{n}) .")
        
        return "\n".join(filter_lst) 
    def make_var_names(self,triples):
        # makes a dictionary with triples of classes to triples with var names
        counter = {}
        query_dict = {}
        for triple in triples:
            query_dict[triple] = {}
            subject = get_local_name(triple.s)
            object = get_local_name(triple.o)
            if subject not in counter.keys():
                counter[subject] = 0
                s_var = subject + str(counter[subject])
            else:
                counter[subject] += 1
                s_var = subject + str(counter[subject])
            if object not in counter.keys():
                counter[object] = 0
                o_var = object + str(counter[object])
            else:
                counter[object] += 1
                o_var = object + str(counter[object])

            query_dict[triple] = Triple(s_var,triple.p,o_var)

        filters = self.add_filters(counter)
        return query_dict, filters
    # query fragments can be list, then list can be continuously concatenated with fragments. fragments can be joined by '\n'
    def add_where(self,query_dict):
        where = []
        for klass, var in query_dict.items():
            where.append(f"?{var.s} a {convert_to_prefixed(klass.s, self.graph)} .")
            where.append(f"?{var.s} {convert_to_prefixed(var.p, self.graph)} ?{var.o} .")
            where.append(f"?{var.o} a {convert_to_prefixed(klass.o, self.graph)} .")
        return '\n'.join(where)
    
    def get_query(self):
        # may need to add prefixes
        query = f"""{self.prefixes}\nSELECT DISTINCT * WHERE {{ {self.where}\n{self.filters} }} """
        return query

# %%

# test_data = [
#     Triple(S223['Connection'], S223['connectsFrom'], S223['HeatExchanger']),
#     Triple(S223['Connection'], S223['connectsFrom'], S223['Junction']),
#     Triple(S223['Connection'], S223['connectsFrom'], S223['Valve']),
#     Triple(S223['Connection'], S223['connectsTo'], S223['AirHandlingUnit']),
#     Triple(S223['Connection'], S223['connectsTo'], S223['Coil']),
#     Triple(S223['Connection'], S223['connectsTo'], S223['Compressor']),
#     Triple(S223['Connection'], S223['connectsTo'], S223['Damper']),
#     ]
# %%
store = Store()
dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")
# store.load(path = "vrf-model.ttl", format = RdfFormat.TURTLE, to_graph=dg)
store.load(path = "test-graph.ttl", format = RdfFormat.TURTLE, to_graph=dg)
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
store.load(path = "223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)

g = Graph(store = 'Oxigraph')
g.parse("vrf-model-cut.ttl", format="turtle")

walk_graph_sequentially(store)
# %%
