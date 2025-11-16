
from algo3 import * 
from tqdm import tqdm

# %%
data_graph = Graph(store = 'Oxigraph')
data_graph.parse("/Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/from-data-graph/s223-example.ttl", format="turtle")

# %%
@dataclass
class BSchemaStatement:
    # NOTE: original_triple maybe always the same as var_triple
    classes: Triple 
    vars: Triple
    original: Triple
    covered_triples: Set[Triple]
    def __init__(self, classes, vars, original):
        self.classes = classes
        self.vars = vars
        self.original = original
        self.covered_triples = set()
    
    def __repr__(self):
        """Better representation for debugging"""
        return f"stmt( classes:{self.classes}, vars {self.vars})"
        
# NOTE: changing triples to bschema statements 
class PatternQuery:
    def __init__(self, triples, graph):
        self.triples = triples
        self.graph = graph
        self.prefixes = get_prefixes(graph)
        self.query_dict = self.make_var_names(triples)
        self.where = self.add_where(self.query_dict)
        self.ask = self.get_ask_query()

    def make_var_names(self, triples):
        query_triples = []
        for stmt in triples:
            class_triple = stmt.classes
            var_triple = stmt.vars
            subject = get_local_name(var_triple[0]).replace("-", "_")
            object = get_local_name(var_triple[2]).replace("-", "_")
            if class_triple[1].startswith("<"):
                p_var = class_triple[1].split("<")[1].split(">")[0]
            else:
                p_var = class_triple[1]
            # TODO: change this down the line probably
            query_triples.append((Triple(class_triple[0], class_triple[1], class_triple[2]), Triple(subject, p_var, object)))
        return query_triples
    
    def add_where(self, query_triples):
        where = []
        added_type_assertions = set()
        
        for klass, var in query_triples:
            # Only add type assertions once per variable
            s_type_key = (var.s, klass.s)
            o_type_key = (var.o, klass.o)
            if s_type_key not in added_type_assertions:
                where.append(f"?{clean_var_name(var.s)} a {convert_to_prefixed(klass.s, self.graph)} .")
                added_type_assertions.add(s_type_key)

            if klass.o != RDFS.Resource:
                if o_type_key not in added_type_assertions:
                    where.append(f"?{clean_var_name(var.o)} a {convert_to_prefixed(klass.o, self.graph)} .")
                    added_type_assertions.add(o_type_key)
                
            if URIRef(var.p) == A:
                continue 

            if URIRef(var.p) in [S223.hasAspect, S223.hasQuantityKind, S223.hasEnumerationKind]:
                # print(f"?{clean_var_name(var.s)} {convert_to_prefixed(URIRef(var.p), self.graph)} {convert_to_prefixed(S223[var.o], self.graph)} .") 
                where.append(f"?{clean_var_name(var.s)} {convert_to_prefixed(URIRef(var.p), self.graph)} {convert_to_prefixed(S223[var.o], self.graph)} .") 
                continue

            where.append(f"?{clean_var_name(var.s)} {convert_to_prefixed(URIRef(var.p), self.graph)} ?{clean_var_name(var.o)} .")
        
        return "\n".join(where)

    def get_ask_query(self):
        query = f"""{self.prefixes}\nASK WHERE {{ {self.where}\n}} LIMIT 1"""
        # print(query)
        return query

# %%
# I don't think this is necessary for the new approach, so just returning node 
def get_or_create_var(node: URIRef, var_counter: Dict = {}) -> str:
        """Create or retrieve variable name for a node"""
        # if node not in var_counter:
        #     var_counter[node] = node  # Store the actual node for variable naming
        return node

def get_class(node: URIRef, data_graph) -> URIRef:
        """Get the class of a node from the data graph"""
        for _, _, o in data_graph.triples((node, A, None)):
            return o
        # # if the node is a class just return the class
        # for _, _, o in data_graph.triples((None, RDF.type, node)):
        #     return node
        # Default to resource, since I"m putting these results back in a graph
        return URIRef("http://www.w3.org/2000/01/rdf-schema#Resource")

# NOTE: updated to create bschema patterns
def create_class_pattern(triple: Tuple[URIRef, URIRef, URIRef], data_graph) -> Tuple[URIRef, URIRef, URIRef]:
        """Create class-based pattern from concrete triples"""
        pattern = []
        # NOTE: not used, should delete if this works
        var_counter = {}
        
        # Get classes
        s_class = get_class(triple[0], data_graph)
        o_class = get_class(triple[2], data_graph)
        
        # # Create variable names
        # s_var = get_or_create_var(triple[0], var_counter)
        # o_var = get_or_create_var(triple[2], var_counter)
        
        # class_triple = Triple(str(s_class), str(triple[1]), str(o_class))
        # var_triple = Triple(s_var, triple[1], o_var)
        # original_triple = Triple(triple[0], triple[1], triple[2])

        return (s_class, triple[1], o_class)
        
        # return BSchemaStatement(class_triple, var_triple, original_triple)

# %%
def get_subgraph_with_hops(
    graph: Graph, 
    central_node: Union[str, rdflib.URIRef], 
    num_hops: int
) -> Graph:
    """
    Extract a subgraph containing all triples within num_hops from central_node,
    including rdf:type information for all entities.
    
    Args:
        graph: The source RDF graph
        central_node: The central node URI (as string or URIRef)
        num_hops: Number of hops to traverse from the central node
    
    Returns:
        A new Graph containing the subgraph
    """
    if isinstance(central_node, str):
        # print("central node is string: ", central_node)
        central_node = rdflib.URIRef(central_node)
    
    subgraph = Graph(store = 'Oxigraph')
    visited_nodes = set()
    current_layer = {central_node}
    
    # Add class information for central node
    for class_uri in graph.objects(central_node, RDF.type):
        subgraph.add((central_node, RDF.type, class_uri))
    
    for hop in range(num_hops):
        next_layer = set()
        
        for node in current_layer:
            if node in visited_nodes:
                continue
            visited_nodes.add(node)
            
            # Get triples where node is subject
            for p, o in graph.predicate_objects(node):
                subgraph.add((node, p, o))
                if isinstance(o, rdflib.URIRef):
                    next_layer.add(o)
                    # Add class information for object
                    for class_uri in graph.objects(o, RDF.type):
                        subgraph.add((o, RDF.type, class_uri))
            
            # Get triples where node is object
            for s, p in graph.subject_predicates(node):
                subgraph.add((s, p, node))
                if isinstance(s, rdflib.URIRef):
                    next_layer.add(s)
                    # Add class information for subject
                    for class_uri in graph.objects(s, RDF.type):
                        subgraph.add((s, RDF.type, class_uri))
        
        current_layer = next_layer
    
    return subgraph

# %%
def create_class_graph(data_graph: Graph):
    class_graph = Graph(store = 'Oxigraph')
    triple_graph = Graph(store = 'Oxigraph')
    triple_schema = []
    
    for triple in data_graph: 
        class_triple = create_class_pattern(triple, data_graph)
        if class_triple in class_graph:
            continue
        else:
            class_graph.add(class_triple)
            triple_graph.add(triple)
            stmt = BSchemaStatement(class_triple, triple, triple)
            triple_schema.append(stmt)
            # if not ('#' in triple[2]):
            #     print('TRIPLE SHOULD BE NAMESPACED')
    # add any triples to triple_graph connecting things already present 
    all_nodes = set([s for s, p, o in triple_graph] + [o for s, p, o in triple_graph])
    for node in all_nodes:
        for node2 in all_nodes:
            for triple in data_graph.triples((node, None, node2)):
                if triple in triple_graph:
                    continue
                else:
                    triple_graph.add(triple)
                    # print('adding triple: ', triple)
    return class_graph, triple_schema, triple_graph

# %%
def compare_to_query(subject, data_graph, triple_graph, query_hops = 1):
    one_hop_graph = get_subgraph_with_hops(data_graph, subject, query_hops)
    _, one_hop_triple_schema, one_hop_triple_graph = create_class_graph(one_hop_graph)

    # all_nodes = set()
    # for s, p, o in one_hop_triple_graph:
    #     all_nodes.add(s)
    #     all_nodes.add(o)
    # for node in list(all_nodes):
    #     if not ('#' in node):
    #         print(node)
    pq = PatternQuery(one_hop_triple_schema, one_hop_graph)
    
    # print(pq.get_ask_query())
    res = triple_graph.query(pq.get_ask_query())
    # print(res.askAnswer)
    if not res.askAnswer:
        # (one_hop_graph - triple_graph).print()
        return False, pq, one_hop_graph
    return True, pq, one_hop_graph

def bind_triples_to_query(subject, subject_class, pq: PatternQuery):
    """Bind triples' values to query variables. 
    All triples have the same subject and object, so we only bind once."""
    
    candidate_stmts = pq.triples
    var_bindings = []
    
    for stmt in candidate_stmts:
        if stmt.classes[0] == subject_class:
            var_bindings.append(clean_var_name(get_local_name(stmt.vars[0])))
    
    if len(var_bindings) == 0:
        # print(f"[BIND] ERROR: Could not find matching pattern for binding!")
        return False
        
    for s_var in var_bindings:
        query = pq.get_ask_query()
        values_clause = f"VALUES (?{s_var}) {{ (<{subject}>) }}"
        
        # print(f"[BIND] VALUES clause: {values_clause}")
        
        # Insert VALUES clause into WHERE clause
        where_pos = query.find("WHERE")
        if where_pos != -1:
            insert_pos = query.find("{", where_pos) + 1
            query = query[:insert_pos] + "\n    " + values_clause + "\n" + query[insert_pos:]
        
        # print(f"[BIND] Final query:\n{query}")
        yield query


# %%
failed_subjects = set()
def compare_all_nodes(data_graph, triple_graph, add_hops = 10):
    matches = 0
    not_matches = 0
    unmatched_subjects = set()
    added_to_triples = 0
    print('Starting Graph Types')
    unmatched_graph = Graph()
    print(f"{triple_graph.store=}, {data_graph.store=}")
    # Add in 'concentric circles' from starting graph
    # adding from 10 concentric circles
    next_circle = triple_graph
    seen_triples = Graph()
    for i in range(add_hops):
        added_at_start = added_to_triples
        added_triples_graph = Graph()
        nodes = set()
        for s, p, o in next_circle:
            nodes.add(s)
            nodes.add(o)
        next_circle = Graph()
        for s in tqdm(list(nodes)):
            # Classes are not being added correctly. Need to handle namespaces better.
            # if not ("#" in s):
            #     # print(s)
            #     continue
            success, pq, one_hop_graph = compare_to_query(subject = s, data_graph = data_graph, triple_graph = triple_graph)
            next_circle += one_hop_graph - triple_graph - seen_triples
            if success:
                #ask the other way
                s_class = get_class(s, data_graph)

                one_hop_triple_graph = get_subgraph_with_hops(triple_graph, s, 1)
                _, one_hop_triple_schema, one_hop_triple_graph = create_class_graph(one_hop_triple_graph)
                pq = PatternQuery(one_hop_triple_schema, one_hop_triple_graph)
                
                bound_queries = bind_triples_to_query(s, s_class, pq)
                check_2_success = False
                query_debug = ""
                for query in bound_queries:
                    # any bound query success means success
                    if one_hop_graph.query(query).askAnswer:
                        check_2_success = True
                        query_debug = query
                    # print(pq.get_ask_query())
            if (check_2_success & success)==False:
                # more messiness, but don't add classes
                failed_subjects.add(s)
                for s,p,o in one_hop_graph:
                    if p == A:
                        continue
                    added_triples_graph.add((s,p,o))
                added_to_triples += 1
            # if len(added_triples_graph) == 0:
            #     print('Failed query but added no triples')
            #     print('failed on subject: ', s)
            #     one_hop_graph.print()
        for s, p, o in added_triples_graph:
            triple_graph.add((s,p,o))
            
        seen_triples += next_circle
        if seen_triples == data_graph:
            print('All triples seen')
            break
        # print('added triples: ', added_to_triples - added_at_start)
        # added_triples_graph.print()

    # print('Graph Types After adjusting triple_graph')
    # print(f"{triple_graph.store=}, {data_graph.store=}")
    # for s, p, o in tqdm(data_graph):
    #     success, pq, unmatched_graph = compare_to_query(subject = s, data_graph = data_graph, triple_graph = triple_graph)
    #     # if s in data_graph.subjects(A, S223.QuantifiableObservableProperty):
    #     #     # print('On a point')
    #     #     if s in data_graph.subjects(S223.hasAspect, None):
    #     #         print('Property with aspect \n')
    #     #         print(pq.get_ask_query())
    #     if success:
    #         matches += 1
    #     else:
    #         not_matches += 1
    #         unmatched_subjects.add(s)
        
    print('Graph Types After query_comparison')
    print(f"{triple_graph.store=}, {data_graph.store=}, {unmatched_graph=}")
    return matches, not_matches, unmatched_subjects, added_to_triples, triple_graph

# %%
if __name__ == 'main':
    data_graph = Graph(store = 'Oxigraph')
    data_graph.parse("/Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/from-data-graph/brick-example.ttl", format="turtle")
    # need to remove empty subject 
    remove_triples = []
    for s, p, o in data_graph:
        if str(get_local_name(s)).strip() == "":
            # print("skipping subject empty string")
            remove_triples.append((s,p,o))
    for triple in remove_triples:
        data_graph.remove(triple)
            
    class_graph, triple_schema, triple_graph = create_class_graph(data_graph)
    matches, not_matches, unmatched_subjects, added_to_triples, new_triple_graph = compare_all_nodes(data_graph = data_graph, triple_graph = triple_graph, add_hops = 5)
    new_triple_graph.serialize('algo4-brick.ttl', format = 'ttl')

    # %%
    print("Matched: ", matches, " Not matched: ", not_matches, "Unique unmatched subjects: ", len(unmatched_subjects))
    print("Added to triples_graph: ", added_to_triples, " times")

    # %%
    triple_graph.print()

    # %%
    for s, p, o in new_triple_graph:
        s_class = get_class(s, new_triple_graph)
        pq = PatternQuery(triple_schema, new_triple_graph)
        # print(pq.get_ask_query())
        bound_queries = bind_triples_to_query(s, s_class, pq)
        break

        
    for query in bound_queries:
        # print(query)
        print(new_triple_graph.query(query).askAnswer)

    # %%

    s223_data_graph = Graph(store = 'Oxigraph')
    s223_data_graph.parse("/Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/from-data-graph/s223-example.ttl", format="turtle")
    s223_bschema = BSchemaGenerator(s223_data_graph)
    s223_class_graph, s223_triple_schema, s223_triple_graph = create_class_graph(s223_data_graph)

    # %%



