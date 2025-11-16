from algo3 import * 
from tqdm import tqdm 

def create_class_graph(mini_bs):
    class_graph = Graph(store = 'Oxigraph')
    triple_graph = Graph(store = 'Oxigraph')
    triple_schema = []
    for triple in mini_bs.all_triples:
        if RDFS.Resource in [triple.s, triple.p, triple.o]:
            continue
        pattern = mini_bs._create_class_pattern([triple])[0]
        print(pattern)
        class_pattern = pattern[0]
        var_pattern = pattern[1]
        original_pattern = pattern[2]
        class_triple = (URIRef(class_pattern.s), URIRef(class_pattern.p), URIRef(class_pattern.o))
        if class_triple in class_graph:
            continue
        else:
            class_graph.add(class_triple)
            triple_schema.append(original_pattern)
            triple_graph.add((original_pattern.s, original_pattern.p, original_pattern.o))
            # if not ('#' in triple.o):
            #     print('TRIPLE SHOULD BE NAMESPACED')
    # add any triples to triple_graph connecting things already present 
    all_nodes = set([s for s, p, o in triple_graph] + [o for s, p, o in triple_graph])
    for node in all_nodes:
        for node2 in all_nodes:
            for triple in mini_bs.data_graph.triples((node, None, node2)):
                if triple in triple_graph:
                    continue
                else:
                    triple_graph.add(triple)
                    # print('adding triple: ', triple)
    return class_graph, triple_schema, triple_graph

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

def compare_to_query(subject, data_graph, triple_graph):
    one_hop_graph = get_subgraph_with_hops(data_graph, subject, 1)
    bschema = BSchemaGenerator(one_hop_graph)
    _, one_hop_triple_schema, one_hop_triple_graph = create_class_graph(bschema)

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
        return False, pq, one_hop_graph - triple_graph
    return True, pq, None

def compare_all_nodes(data_graph, triple_graph, add_hops = 10):
    matches = 0
    not_matches = 0
    unmatched_subjects = set()
    added_to_triples = 0
    print('Starting Graph Types')
    print(f"{triple_graph.store=}, {data_graph.store=}")
    # Add in 'concentric circles' from starting graph
    # adding from 10 concentric circles
    for i in range(add_hops):
        added_at_start = added_to_triples
        added_triples_graph = Graph()
        nodes = set()
        for s, p, o in triple_graph:
            nodes.add(s)
            nodes.add(o)
        for s in tqdm(list(nodes)):
            # Classes are not being added correctly. Need to handle namespaces better.
            if not ("#" in s):
                # print(s)
                continue
            success, pq, one_hop_graph = compare_to_query(subject = s, data_graph = data_graph, triple_graph = triple_graph)
            if success:
                continue
            else:
                for s,p,o in one_hop_graph:
                    added_triples_graph.add((s,p,o))
                added_to_triples += 1
            # if len(added_triples_graph) == 0:
            #     print('Failed query but added no triples')
            #     print('failed on subject: ', s)
            #     one_hop_graph.print()
        for s, p, o in added_triples_graph:
            triple_graph.add((s,p,o))
        print('added triples: ', added_to_triples - added_at_start)
        added_triples_graph.print()

    print('Graph Types After adjusting triple_graph')
    print(f"{triple_graph.store=}, {data_graph.store=}")
    for s, p, o in tqdm(data_graph):
        success, pq, unmatched_graph = compare_to_query(subject = s, data_graph = data_graph, triple_graph = triple_graph)
        # if s in data_graph.subjects(A, S223.QuantifiableObservableProperty):
        #     # print('On a point')
        #     if s in data_graph.subjects(S223.hasAspect, None):
        #         print('Property with aspect \n')
        #         print(pq.get_ask_query())
        if success:
            matches += 1
        else:
            not_matches += 1
            unmatched_subjects.add(s)
        
    print('Graph Types After query_comparison')
    print(f"{triple_graph.store=}, {data_graph.store=}, {unmatched_graph=}")
    return matches, not_matches, unmatched_subjects, added_to_triples, triple_graph

s223_data_graph = Graph(store = 'Oxigraph')
s223_data_graph.parse("/Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/from-data-graph/s223-example.ttl", format="turtle")
s223_bschema = BSchemaGenerator(s223_data_graph)
s223_class_graph, s223_triple_schema, s223_triple_graph = create_class_graph(s223_bschema)
matches, not_matches, unmatched_subjects, added_to_triples, s223_new_triple_graph = compare_all_nodes(data_graph = s223_data_graph, triple_graph = s223_triple_graph)
s223_new_triple_graph.serialize('algo3-s223.ttl', format = 'ttl')
# s223_new_triple_graph.print()
print("Matched: ", matches, " Not matched: ", not_matches, "Unique unmatched subjects: ", len(unmatched_subjects))
print("Added to triples_graph: ", added_to_triples, " times")