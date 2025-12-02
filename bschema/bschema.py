from rdflib.compare import isomorphic, graph_diff

from pprint import pprint
from typing import Union, List, Union, Tuple, Optional
from rdflib import Graph, URIRef, Literal
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
    num_hops: int = 1,
    get_classes = False
) -> Graph:
    """
    Extract a subgraph containing all triples within num_hops from central_node,
    including rdf:type information for all entities.
    
    Args:
        graph: The source RDF graph
        central_node: The central node URI (as string or URIRef)
        num_hops: Number of hops to traverse from the central node
        get_classes: Whether to include rdf:type information for all entities
    
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

def get_class(node: URIRef, data_graph: Graph) -> URIRef:
        """Get the class of a node from the data graph. Asigns a default class for literals or if one is not found"""
        # NOTE: can change to look at union of classes, if necessary for differrent use of ontologies
        for _, _, o in data_graph.triples((node, A, None)):
            if str(BS) in str(o):
                return o
        for _, _, o in data_graph.triples((node, A, None)):
            return o
        if isinstance(node, Literal):
            return URIRef("http://www.w3.org/2000/01/rdf-schema#Literal")
        return URIRef("http://www.w3.org/2000/01/rdf-schema#Resource")

def create_class_pattern(triple: Tuple[URIRef, URIRef, URIRef], data_graph) -> Tuple[URIRef, URIRef, URIRef]:
        """Create class-based pattern from a triple. This is just how the class of the subject relates to the class of the object.
        If NamedNodes are used (i.e. hasAspect, hasEnumerationKind, etc.) then the named node is used as the class."""
        # TODO: should be able to be appended to or overwritten outside of the class
        named_node_predicates = [S223.hasAspect, S223.hasEnumerationKind, S223.hasQuantityKind, S223.hasUnit, 
                                 S223.hasMedium, S223.ofConstituent, QUDT.hasUnit, S223.hasRole, S223.hasDomain, 
                                 BRICK.hasUnit, QUDT.hasQuantityKind]
        s_class = get_class(triple[0], data_graph)
        if triple[1] == A:
            o_class = triple[2]
        elif triple[1] in named_node_predicates:
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

def get_class_isomorphisms(data_graph, similarity_threshold = None):
    """Looks for isomorphisms or high similarities between the graphs one hop around each node in the data graph.
    If similarity threshold is none, isomorphisms are found. If not, similar nodes are found
    based on the overlap coefficent of the one-hop subgraphs around these nodes.
    
    Args:
        data_graph: The data graph
        similarity_threshold: The threshold for similarity between graphs. If None, isomorphisms are found.
    
    Returns:
        A list of distinct_class_subgraphs,
        a list of all the subjects seen
        a list of which subjects are equivalent
        a list of the classes for these equivalent subjects
        
        distinct_class_subgraphs, seen_subjects, equivalent_subjects, subject_classes
    """
    
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
        for i in indices:
            g = distinct_class_subgraphs[i]
            if similarity_threshold is not None:
                in_both, _, _ = graph_diff(class_graph, g)
                intersection_size = len(in_both)
                similarity_score = intersection_size / min(len(class_graph), len(g))
                
                if similarity_score > similarity_threshold:
                    # NOTE: May not want to use + because we lose oxigraph as the store, also not sure it works correctly. Maybe just take the bigger graph?
                    distinct_class_subgraphs[i] = class_graph + g
                    equivalent_subjects[i].append(s)
                    found_in_preferred = True
                    add_subgraph = False
                    break
                else:
                    found_in_preferred = False
                    add_subgraph = True
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

        if indices == []:
            add_subgraph = True

        if add_subgraph == True:
            distinct_class_subgraphs.append(class_graph)
            equivalent_subjects.append([s])
            subject_classes.append(subject_class)
    return distinct_class_subgraphs, seen_subjects, equivalent_subjects, subject_classes

# TODO: consider switching to overlap coefficient rather than jaccard, so that unions work better 
def find_similar_sublists(list1, list2, min_intersection_ratio=0.4, use_jaccard=True):
    """
    Find pairs of sublists that have high overlap but aren't exactly the same.
    This is a debugging function to see how groups of nodes change per iteration when creating the bschema
    
    Args:
        list1: First list containing sublists
        list2: Second list containing sublists
        min_intersection_ratio: Minimum ratio of intersection to consider (default 0.8)
        use_jaccard: Whether to use Jaccard similarity or overlap coefficient (default to True, Jaccard)
    
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

            # calculate overlap coefficient
            overlap_coefficient = len(intersection) / min(len(set1), len(set2))
            
            # Check if meets threshold
            threshold_met = False
            if use_jaccard:
                threshold_met = jaccard >= min_intersection_ratio
            else:
                threshold_met = overlap_coefficient >= min_intersection_ratio
            
            # Add pair if meets threshold
            if threshold_met:
                similar_pairs.append({
                    'list1_index': i,
                    'list2_index': j,
                    'jaccard_similarity': jaccard,
                    'overlap_coefficient': overlap_coefficient,
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
    """creates a copy of a graph using Oxigraph"""
    g2 = Graph(store = "Oxigraph")
    bind_prefixes(g2)
    for triple in g:
        g2.add(triple)
    return g2


# TODO: cleanup renaming
def assign_new_classes(data_graph, distinct_class_subgraphs, equivalent_subjects, subject_classes, use_original_names):
    class_mappings = {}
    new_subject_classes = {}
    for i, subj_list in enumerate(equivalent_subjects):
        if use_original_names:
            name = common_pattern(subj_list)
            if BNODE_BASE in name:
                name = 'bnode'
            counter[name] = count = counter.get(name, 0) + 1
            name_no_uri = name.split('#')[-1].split('/')[-1]
            # new_cls_name = URIRef(f"{name}{count}")
            new_cls_name = BS[f"{name_no_uri}{count}"]
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
    """ Create a bschema from a data graph."""
    global counter
    counter = {}
    class_mappings = []
    original_data_graph.remove((URIRef('urn:example#'), A, OWL.Ontology))
    data_graph = copy_graph(original_data_graph)
    data_graph = data_graph.skolemize()
    for iteration in range(iterations):
        # TODO: need to double check if it works to reset the counter each time, or if it will create issues because of when class name is assigned
        counter = {}
        distinct_class_subgraphs, seen_subjects, equivalent_subjects, subject_classes = get_class_isomorphisms(data_graph, similarity_threshold)
        new_subject_classes, new_class_mappings = assign_new_classes(data_graph, distinct_class_subgraphs, equivalent_subjects, subject_classes, use_original_names=use_original_names)
        class_mappings.append(new_class_mappings)

        if iteration >= 1:
            # stop condition is no subjects are being distinguished from each other
            if lists_have_same_members(equivalent_subjects, prev_equivalent_subjects):
                print('Algorithm stopped, since no further distinguishing classes found. Process took ',iteration, 'iterations')
                if PRINT_GRAPHS:
                    print('Printing Last Set Difference')
                    pprint(last_set_diff)
                break
            else:
                last_set_diff = find_similar_sublists(equivalent_subjects, prev_equivalent_subjects)
    
        prev_equivalent_subjects = equivalent_subjects
        # delete BS class since it is no longer needed 
        # NOTE: hacky method of addressing getting the right class or class set
        if iteration >= 1:
            for s, cls_name in prev_subject_classes.items():
                data_graph.remove((s, A, cls_name))
        
        # add new class names
        for s, cls_name in new_subject_classes.items():
            data_graph.add((s, A, cls_name))
        
        prev_subject_classes = new_subject_classes
        print("Summarized Graph Length: ", len(create_class_graph(data_graph)))
        # Threshold 0 is just the class graph, and requires only 1 iteration
        if similarity_threshold == 0:
            break
    
    
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
    return class_graph, member_graph, iteration