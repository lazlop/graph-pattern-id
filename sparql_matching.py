# %%
from dataclasses import dataclass
from pyoxigraph import * 
from namespaces import *
from rdflib import Graph, URIRef

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
store.load(path = "test-graph.ttl", format = RdfFormat.TURTLE, to_graph=dg)
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
store.load(path = "223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)

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
                if direction == 'incoming' and s not in visited:
                    groups.append(
                                  (Triple(str(get_class(s)), str(p), str(get_class(o))),
                                   Triple(str(s), str(p), str(o))
                                   )
                    )
                elif direction == 'outgoing' and o not in visited:
                    groups.append(
                                  (Triple(str(get_class(o)), str(p), str(get_class(s))),
                                   Triple(str(o), str(p), str(s))
                                   )
                    )

                p = PatternQuery(groups)
                print(p.query)
                print('QUERYING FOR: ', current_node, "ON PATH: ", path)
                print('RESULTS')
                res = store.query(p.query, default_graph = [dg])
                print(res.serialize(format = QueryResultsFormat.TSV).decode('utf-8'))

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
        for class_triple, var_triple in triples:
            query_dict[class_triple] = {}
            subject = get_local_name(var_triple.s)
            object = get_local_name(var_triple.o)
            if subject not in counter.keys():
                counter[subject] = 0
                s_var = subject
            else:
                counter[subject] += 1
                s_var = subject + '_' + str(counter[subject])
            if object not in counter.keys():
                counter[object] = 0
                o_var = object
            else:
                counter[object] += 1
                o_var = object + '_' + str(counter[object])

            # have to remove angle brackets from predicate
            p_var = class_triple.p.split('<')[1].split('>')[0]
            query_dict[class_triple] = Triple(s_var,p_var,o_var)
        filters = self.add_filters(counter)
        return query_dict, filters
    # query fragments can be list, then list can be continuously concatenated with fragments. fragments can be joined by '\n'
    def add_where(self,query_dict):
        where = []
        for klass, var in query_dict.items():
            where.append(f"?{var.s} a {convert_to_prefixed(klass.s,g)} .")
            where.append(f"?{var.s} {convert_to_prefixed(URIRef(var.p),g)} ?{var.o} .")
            where.append(f"?{var.o} a {convert_to_prefixed(klass.o, g)} .")
        return '\n'.join(where)
    
    def get_query(self):
        # may need to add prefixes
        query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {self.where}\n{self.filters} }} """
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

# g = Graph(store = 'Oxigraph')
# g.parse("vrf-model-cut.ttl", format="turtle")

path = walk_graph_sequentially(store)
# %%
