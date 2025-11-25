"""Notes:
LLM class naming isn't particularly good using a locally running LLM. Should just number the variants of the original class. (ConnectionPoint1,2, VAV1,2, etc.)
Using GPT OSS run by CBORG, creating new class names was decent
 
TODO: 
- works right for brick, but class graph currently only contains one class. This may create bugs, so I will need to consider other methods. Working so far because it happens to gets the most recently added class, which is alphabetically the latest because of the version tag I'm adding. Instead of directly doing the class relations it may make sense to separate instance and class once again 
- Fix how I'm getting aspects and named nodes again so these show up in class graph for isomorphism. 
- Getting the class names relies on how graph is serialized to get most recently added class label. This may cause a bug in the future.
- Fix relaxed version of b_schema using jaccard similarity. May not converge exactly right since different subgraphs can be selected for each loop
- Need to check stop condition for jaccard similarity version. NOT working correctly for mortar
    A hint about what may be going wrong is that the graphs are getting bigger per iteration. I think they shouldn't be getting bigger after the 1st iteration because I'm just removing and replacing labels
    Ran with 20 iterations and the graph got one longer per iteration, and the summarized graph got 3 longer.
    Appears that there were different amounts of rooms and the amount of rooms per floor changed a bit
    Also appears that there was an extra external reference version added 
    This indicates a bug with the rdfs:Resource usage. Line 108 in bldg5-20iter shows this. There should not be multiple external references on this sensor
    BUG IS BLANK NODES. Will skolemize graph before doing anything. Now stop condition is doing something for jaccard at least.
- Should Jaccard similarity require things to be the same class? Perhaps that is an additional layer of relaxation we can consider later.
"""

from rdflib.compare import isomorphic, graph_diff

from pprint import pprint
from typing import Union, List, Union, Tuple, Optional
from rdflib import Graph, URIRef
import sys
from .utils import * 
from .namespaces import *

from tqdm import tqdm

counter = {}
bnode_counter = {}
PRINT_GRAPHS = False

def get_subgraph_with_hops(
    graph: Graph, 
    central_node: Union[str, URIRef], 
    num_hops: int,
    get_classes = False
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
        central_node = URIRef(central_node)
    
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
                if isinstance(o, URIRef):
                    next_layer.add(o)
                    # Add class information for object
                    for class_uri in graph.objects(o, RDF.type):
                        subgraph.add((o, RDF.type, class_uri))
            
            # Get triples where node is object
            for s, p in graph.subject_predicates(node):
                subgraph.add((s, p, node))
                if isinstance(s, URIRef):
                    next_layer.add(s)
                    # Add class information for subject
                    for class_uri in graph.objects(s, RDF.type):
                        subgraph.add((s, RDF.type, class_uri))
        
        current_layer = next_layer
    if get_classes:
        for s, p, o in subgraph:
            for class_uri in graph.objects(s, RDF.type):
                subgraph.add((s, RDF.type, class_uri))
            for class_uri in graph.objects(o, RDF.type):
                subgraph.add((o, RDF.type, class_uri))
    return subgraph

def get_class(node: URIRef, data_graph) -> URIRef:
        """Get the class of a node from the data graph"""
        # TODO: Shouldn't hve a default class and need a union of classes
        # Should have something else to represent literals, other than resource, but need to make sure defualt just applies to literals
        
        # NOTE: hacky method of addressing getting the right class or class set, just by preferring BS classes and earlier making sure hteres just one BS class per thing
        for _, _, o in data_graph.triples((node, A, None)):
            if str(BS) in str(o):
                return o
        for _, _, o in data_graph.triples((node, A, None)):
            return o
        return URIRef("http://www.w3.org/2000/01/rdf-schema#Resource")

def create_class_pattern(triple: Tuple[URIRef, URIRef, URIRef], data_graph) -> Tuple[URIRef, URIRef, URIRef]:
        """Create class-based pattern from concrete triples"""
        # may want to have a union of classes 
        # TODO: if ordering is not consistent of classes this could create bugs
        # subject node should maybe represent union of classes
        named_node_predicates = [S223.hasAspect, S223.hasEnumerationKind, S223.hasQuantityKind, S223.hasUnit, S223.hasMedium, S223.ofConstituent]
        s_class = get_class(triple[0], data_graph)
        if triple[1] == A:
            o_class = triple[2]
        elif triple[1] in [S223['hasAspect'], S223.hasEnumerationKind, S223.hasQuantityKind, S223.hasUnit]:
            o_class = triple[2]
        else:
            o_class = get_class(triple[2], data_graph)
        return (s_class, triple[1], o_class)

def create_class_graph(data_graph: Graph):
    class_graph = Graph(store = 'Oxigraph')
    for triple in data_graph: 
        class_triple = create_class_pattern(triple, data_graph)
        if class_triple in class_graph:
            continue
        else:
            class_graph.add(class_triple)

    return class_graph

def create_class_graph(data_graph: Graph):
    class_graph = Graph(store = 'Oxigraph')
    for triple in data_graph: 
        class_triple = create_class_pattern(triple, data_graph)
        if class_triple in class_graph:
            continue
        else:
            class_graph.add(class_triple)

    return class_graph

def get_class_isomorphisms(data_graph, similarity_threshold = None):
    distinct_class_subgraphs = []
    seen_subjects = set()
    equivalent_subjects = []
    subject_classes = []
    for s,p,o in tqdm(data_graph):
        add_subgraph = False
        found_in_preferred = False
        subject_class = get_class(s, data_graph)
        if s in seen_subjects:
            continue
        else:
            seen_subjects.add(s)
        subgraph = get_subgraph_with_hops(data_graph, s, 1)
        class_graph = create_class_graph(subgraph)
        if equivalent_subjects == []:
            equivalent_subjects.append([s])
            distinct_class_subgraphs.append(class_graph)
            subject_classes.append(subject_class)
            continue
            
        indices = [i for i, x in enumerate(subject_classes) if x == subject_class]
        # check indices first 
        # NOTE: checking indices like this places an extra condition on the jaccard similarity.
        for i in indices:
            g = distinct_class_subgraphs[i]
            if similarity_threshold is not None:
                in_both, in_g1_only, in_g2_only = graph_diff(class_graph, g)
                intersection_size = len(in_both)
                union_size = len(in_both) + len(in_g1_only) + len(in_g2_only)

                if union_size > 0:
                    similarity_score = intersection_size / union_size
                    # NOTE: also replacing matched graph with union of class graph and g
                    if similarity_score > similarity_threshold:
                        # NOTE: May not want to use + because we lose oxigraph as the store, also not sure it works correctly. Maybe just take the bigger graph?
                        distinct_class_subgraphs[i] = class_graph + g
                        # if len(class_graph) > len(g):
                        #     distinct_class_subgraphs[i] = class_graph
                        # else:
                        #     distinct_class_subgraphs[i] = g
                        
                        equivalent_subjects[i].append(s)
                        found_in_preferred = True
                        add_subgraph = False
                        break
                    else:
                        found_in_preferred = False
                        add_subgraph = True
            # NOTE: It may be good to look for isomorphic first then within jaccard similarity second to prefer exact matches. But it would run slower, and jaccard is just for testing on mortar rn
            else:
                if isomorphic(class_graph, g): 
                    equivalent_subjects[i].append(s)
                    found_in_preferred = True
                    add_subgraph = False
                    break
                else:
                    found_in_preferred = False
                    add_subgraph = True

        if found_in_preferred:
            continue

        # NOTE: may be a more efficient way to do this. Not sure it does anything since for an isomorphism to be found the subject classes must be the same. This is also an extra condition for jaccard similarity
        # In mortar I'm finding many more isomorphisms, maybe this is because the one hop graphs are identical for subjects with different classes? 
        # TODO: Finding unexpected isomorphisms for empty graphs. Should handle somehow
        # for i, g in enumerate(distinct_class_subgraphs):
        #     if isomorphic(class_graph, g): 
        #         pprint(subject_class)
        #         pprint(subject_classes)
        #         print('FOUND unexpected isomorphism')
        #         class_graph.print()
        #         g.print()
        #         raise Exception
        #         equivalent_subjects[i].append(s)
        #         add_subgraph = False
        #         break
        #     else:
        #         add_subgraph = True

        if indices == []:
            add_subgraph = True

        if add_subgraph == True:
            distinct_class_subgraphs.append(class_graph)
            equivalent_subjects.append([s])
            subject_classes.append(subject_class)
    return distinct_class_subgraphs, seen_subjects, equivalent_subjects, subject_classes

def find_similar_sublists(list1, list2, min_intersection_ratio=0.4):
    """
    Find pairs of sublists that have high overlap but aren't exactly the same.
    
    Args:
        list1: First list containing sublists
        list2: Second list containing sublists
        min_intersection_ratio: Minimum ratio of intersection to consider (default 0.8)
    
    Returns:
        list: Pairs of similar but not identical sublists with their similarity info
    """
    similar_pairs = []
    
    for i, sublist1 in enumerate(list1):
        set1 = set(sublist1)
        
        for j, sublist2 in enumerate(list2):
            set2 = set(sublist2)
            
            # Skip if they're exactly the same
            if set1 == set2:
                continue
            
            # Calculate intersection and union
            intersection = set1 & set2
            union = set1 | set2
            
            # Calculate Jaccard similarity
            jaccard = len(intersection) / len(union) if union else 0
            
            # Also calculate intersection ratio relative to each set
            ratio1 = len(intersection) / len(set1) if set1 else 0
            ratio2 = len(intersection) / len(set2) if set2 else 0
            
            # Check if meets threshold
            if jaccard >= min_intersection_ratio:
                similar_pairs.append({
                    'list1_index': i,
                    'list2_index': j,
                    'jaccard_similarity': jaccard,
                    'intersection_size': len(intersection),
                    'only_in_list1': list(set1 - set2),
                    'only_in_list2': list(set2 - set1),
                    'common': list(intersection),
                    'size_list1': len(set1),
                    'size_list2': len(set2)
                })
    
    return similar_pairs

def lists_have_same_members(list1, list2):
    """Check if two lists with sublists have same members, regardless of order."""
    if len(list1) != len(list2):
        return False
    
    # Convert each sublist to a frozenset and compare as sets
    sets1 = {frozenset(sublist) for sublist in list1}
    sets2 = {frozenset(sublist) for sublist in list2}
    
    return sets1 == sets2

def copy_graph(g):
    g2 = Graph(store = "Oxigraph")
    bind_prefixes(g2)
    for triple in g:
        g2.add(triple)
    return g2


def assign_new_classes(data_graph, distinct_class_subgraphs, equivalent_subjects, subject_classes, use_original_names):
    class_mappings = {}
    new_subject_classes = {}
    for i, subj_list in enumerate(equivalent_subjects):
        if use_original_names:
            name = common_pattern(subj_list)
            if BNODE_BASE in name:
                name = 'bnode'
            counter[name] = count = counter.get(name, 0) + 1
            new_cls_name = URIRef(f"{name}{count}")
        else:
            cls_name = subject_classes[i]
            name = cls_name.split('#')[-1].split('_version_')[0]
            counter[name] = count = counter.get(name, 0) + 1
            new_cls_name = URIRef(f"{name}_version_{count}")
        for s in subj_list:
            new_subject_classes.update({s: BS[new_cls_name.split('#')[-1]]})
            class_mappings[new_cls_name] = (subject_classes[i], distinct_class_subgraphs[i])

    return new_subject_classes, class_mappings


def create_bschema(original_data_graph, iterations = 10, similarity_threshold = None, remove_added_labels = True, use_original_names = True):
    # need to remove ontology statement because having just the prefix breaks serialization/parsing by oxigraph
    global counter
    counter = {}
    class_mappings = []
    original_data_graph.remove((URIRef('urn:example#'), A, OWL.Ontology))
    data_graph = copy_graph(original_data_graph)
    data_graph = data_graph.skolemize()
    for i in range(iterations):
        # TODO: need to double check if it works to reset the counter each time, or if it will create issues because of when class name is assigned
        counter = {}
        distinct_class_subgraphs, seen_subjects, equivalent_subjects, subject_classes = get_class_isomorphisms(data_graph, similarity_threshold)
        new_subject_classes, new_class_mappings = assign_new_classes(data_graph, distinct_class_subgraphs, equivalent_subjects, subject_classes, use_original_names=use_original_names)
        class_mappings.append(new_class_mappings)

        if i >= 1:
            # stop condition is no subjects are being distinguished from each other
            if lists_have_same_members(equivalent_subjects, prev_equivalent_subjects):
                print('Algorithm stopped, since no further distinguishing classes found. Process took ',i, 'iterations')
                if PRINT_GRAPHS:
                    print('Printing Last Set Difference')
                    pprint(last_set_diff)
                break
            else:
                last_set_diff = find_similar_sublists(equivalent_subjects, prev_equivalent_subjects)
    
        prev_equivalent_subjects = equivalent_subjects
        # delete BS class since it is no longer needed 
        # NOTE: hacky method of addressing getting the right class or class set
        if i >= 1:
            for s, cls_name in prev_subject_classes.items():
                data_graph.remove((s, A, cls_name))
        
        # add new class names
        for s, cls_name in new_subject_classes.items():
            data_graph.add((s, A, cls_name))
        
        prev_subject_classes = new_subject_classes
        print("Summarized Graph Length: ", len(create_class_graph(data_graph)))
    
    
    # H, in the paper
    class_graph = create_class_graph(data_graph)

    # TODO: Should handle added class labels with better method. 
    if remove_added_labels:
        for s,p,o in class_graph:
            if (p == A) & (str(BS) in str(o)):
                class_graph.remove((s,p,o))
    # M, in the paper 
    member_graph = Graph(store = "Oxigraph")
    for i in range(len(equivalent_subjects)):
        # TODO: Seq should probably actually be Alt or other Bag, not much value in the sequence
        member_graph.add((subject_classes[i], A, RDF.Seq))
        for s in equivalent_subjects[i]:
            member_graph.add((subject_classes[i], RDFS.member, s))
    # could optionally also return data_graph, class_mappings
    # also giving amt of iterations
    return class_graph, member_graph, i 