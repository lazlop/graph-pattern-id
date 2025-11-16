from pprint import pprint
from typing import Union, List, Union, Tuple, Optional
from matplotlib import pyplot as plt
import time 
from dataclasses import dataclass
from pyoxigraph import *
from rdflib import Graph, URIRef
from collections import defaultdict
from itertools import combinations
import pandas as pd
import numpy as np
from IPython.display import display
import networkx as nx
import sys
import hashlib
import rdflib
sys.path.append('../utils')
sys.path.append('../../utils')
from namespaces import *
from utils import * 
from dataclasses import dataclass
from typing import Union, Set
from collections import defaultdict
from itertools import combinations
from rdflib import URIRef, Graph
import random


# Implementation doesn't reqlly catch all the triples in a graph, especially things without classes or that may be unconnected


@dataclass(frozen=True)
class Triple:
    s: Union[str, list]
    p: Union[str, list]
    o: Union[str, list]


class PatternQuery:
    def __init__(self, triples, graph=None):
        self.triples = triples
        self.graph = graph
        self.prefixes = get_prefixes(graph)
        self.query_dict = self.make_var_names(triples)
        self.filters = self.add_filters(self.query_dict)
        self.where = self.add_where(self.query_dict)
        self.construct = self.add_construct(self.query_dict)
        self.queries = self.get_query()
        self.construct_query = self.get_construct_query()

    def add_filters(self, triples):
        filter_lst = []
        filter_dict = defaultdict(set)
        for class_triple, var_triple in triples:
            filter_dict[class_triple.s].add(var_triple.s)
            filter_dict[class_triple.o].add(var_triple.o)
        for klass, var_list in filter_dict.items():
            # SO hacky but getting AI code to work... 
            if URIRef(klass) == URIRef("http://www.w3.org/2000/01/rdf-schema#Resource"):
                continue
            if len(var_list) == 1:
                continue
            for var_1, var_2 in combinations(var_list, 2):
                filter_lst.append(f"FILTER (?{var_1} != ?{var_2}) .")

        return "\n".join(filter_lst)

    def make_var_names(self, triples):
        query_triples = []
        for class_triple, var_triple in triples:
            subject = self.get_local_name(var_triple.s).replace("-", "_")
            object = self.get_local_name(var_triple.o).replace("-", "_")
            if class_triple.p.startswith("<"):
                p_var = class_triple.p.split("<")[1].split(">")[0]
            else:
                p_var = class_triple.p
            query_triples.append((class_triple, Triple(subject, p_var, object)))
        return query_triples

    def get_local_name(self, node):
        node = str(node).replace("<", "").replace(">", "")
        if "#" in node:
            return node.rpartition("#")[-1]
        else:
            return node.rpartition("/")[-1]
    
    # NOTE: Shouldn't have used AI generated code for this - took as long or longer to debug as it would have taken to just write... 
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

            
            if klass.o != "http://www.w3.org/2000/01/rdf-schema#Resource":
                if o_type_key not in added_type_assertions:
                    where.append(f"?{clean_var_name(var.o)} a {convert_to_prefixed(klass.o, self.graph)} .")
                    added_type_assertions.add(o_type_key)
                
            if URIRef(var.p) == A:
                continue 
            where.append(f"?{clean_var_name(var.s)} {convert_to_prefixed(URIRef(var.p), self.graph)} ?{clean_var_name(var.o)} .")
        
        return "\n".join(where)

    def add_construct(self, query_triples):
        """Create CONSTRUCT clause to reconstruct the graph pattern"""
        construct = []
        added_type_assertions = set()
        
        for klass, var in query_triples:
            s_type_key = (var.s, klass.s)
            o_type_key = (var.o, klass.o)

            # may need to get rid of dots
            if s_type_key not in added_type_assertions:
                construct.append(f"?{clean_var_name(var.s)} a {convert_to_prefixed(klass.s, self.graph)} .")
                added_type_assertions.add(s_type_key)
            
            if klass.o != "http://www.w3.org/2000/01/rdf-schema#Resource":
                if o_type_key not in added_type_assertions:
                    construct.append(f"?{clean_var_name(var.o)} a {convert_to_prefixed(klass.o, self.graph)} .")
                    added_type_assertions.add(o_type_key)

            if URIRef(var.p) == A:
                continue 
            construct.append(f"?{clean_var_name(var.s)} {convert_to_prefixed(URIRef(var.p), self.graph)} ?{clean_var_name(var.o)} .")
        
        return "\n".join(construct)

    def get_query(self):
        query = f"""{self.prefixes}\nSELECT DISTINCT * WHERE {{ {self.where}\n{self.filters} }}"""
        # query = f"""{self.prefixes}\nSELECT (COUNT(*) as ?count) WHERE {{ {self.where}\n }} LIMIT {int(len(self.graph)/10)}"""
        # query = f"""{self.prefixes}\nSELECT (COUNT(*) as ?count) WHERE {{ {self.where}\n }} LIMIT 1"""
        return query
    
    def get_construct_query(self, offset = 0):
        """Generate CONSTRUCT query to reconstruct graph"""
        # query = f"""{self.prefixes}\nCONSTRUCT {{\n{self.construct}\n}} WHERE {{\n{self.where}\n{self.filters}\n}}"""
        # adding limit. 
        query = f"""{self.prefixes}\nCONSTRUCT {{\n{self.construct}\n}} WHERE {{\n{self.where}\n{self.filters}\n}}LIMIT {int(len(self.graph)/10)}"""
        query = f"""{self.prefixes}\nCONSTRUCT {{\n{self.construct}\n}} WHERE {{\n{self.where}\n}} LIMIT 1"""
        query = f"""{self.prefixes}\nCONSTRUCT {{\n{self.where}\n}} WHERE {{\n{self.where}\n}} LIMIT 10 OFFSET {offset}"""
        return query


class BSchemaAlgorithm:
    def __init__(self, data_graph):
        """
        Initialize the B-Schema algorithm
        :param data_graph: RDFLib Graph containing the data
        """
        self.data_graph = data_graph
        self.b_schema_triples = []  # List of (class_triple, var_triple) tuples
        self.b_schema_set = set()  # Set for quick lookup
        self.represented_triples = Graph(store="Oxigraph")
        self.all_triples = data_graph
        
    def get_triple_class_info(self, triple):
        """
        Get class information for a triple (subject class, predicate, object class)
        """
        s, p, o = triple
        
        # Get subject class
        s_classes = list(self.data_graph.objects(s, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")))
        s_class = s_classes[0] if s_classes else URIRef("http://www.w3.org/2000/01/rdf-schema#Resource")
        
        # Get object class  
        o_classes = list(self.data_graph.objects(o, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")))
        o_class = o_classes[0] if o_classes else URIRef("http://www.w3.org/2000/01/rdf-schema#Resource")
        
        return Triple(str(s_class), str(p), str(o_class)), Triple(str(s), str(p), str(o))
    
    def get_connected_triples(self, node):
        """
        Get all triples connected to a node (where node is subject or object)
        """
        connected = []
        for s, p, o in self.data_graph:
            if s == node or o == node:
                connected.append((s, p, o))
        return connected
    
    def get_nodes_in_schema(self):
        """Get all nodes (subjects and objects) currently in the b-schema"""
        nodes = set()
        for class_triple, var_triple in self.b_schema_triples:
            nodes.add(var_triple.s)
            nodes.add(var_triple.o)
        return nodes
    
    def triple_pattern_in_schema(self, class_triple):
        """Check if a class triple pattern is already in the schema"""
        for existing_class, _ in self.b_schema_triples:
            if (existing_class.s == class_triple.s and 
                existing_class.p == class_triple.p and 
                existing_class.o == class_triple.o):
                return True
        return False
    
    def run(self, max_iterations=150, threshold = 0.95):
        """
        Execute the B-Schema algorithm
        """
        step = 0
        
        print(f"Total triples in data graph: {len(self.all_triples)}")
        triple_element_frequencies = count_nodes(self.data_graph)
        node_counts = Counter()
        node_new_triple_counts = Counter()
        
        while len(self.represented_triples) < len(self.all_triples) and step < max_iterations:
            step += 1
            print(f"\n{'='*60}")
            print(f"Step {step}")
            print(f"{'='*60}")
            
            # Step 1: Add a node to the b-schema graph
            if step == 1:
                # First step: add a random triple
                random_triple = random.choice(list(self.all_triples))
                class_triple, var_triple = self.get_triple_class_info(random_triple)
                self.b_schema_triples.append((class_triple, var_triple))
                self.b_schema_set.add((class_triple.s, class_triple.p, class_triple.o))
                print(f"Added initial triple: {random_triple}")
                print(f"Class pattern: ({class_triple.s}, {class_triple.p}, {class_triple.o})")
            else:
                # Add a node connected to the existing graph
                schema_nodes = self.get_nodes_in_schema()
                print(f"Current schema nodes: {len(schema_nodes)}")
                
                # Find triples not yet represented that connect to schema
                candidate_triples = []
                preferred_triples = []
                # skip literals
                for triple in self.all_triples:
                    if isinstance(triple, rdflib.Literal):
                        continue
                    if triple in self.represented_triples:
                        continue
                    # if the triple's class is already represented maybe we skip it?
                    # this won't get us very far though - need a better pruning method. 
                    candidate_triples.append(triple)
                    # if ((triple[0], None, None) in self.represented_triples) or \
                    #     ((None, None, triple[2]) in self.represented_triples) or \
                    #     ((triple[2], None, None) in self.represented_triples) or \
                    #     ((None, None, triple[0]) in self.represented_triples):
                    #     preferred_triples.append(triple)
                    if ((triple[2], None, None) in self.b_schema_triples) or \
                        ((None, None, triple[0]) in self.b_schema_triples):
                        preferred_triples.append(triple)
                
                print(f"Found {len(candidate_triples)} candidate triples")
                print(f"Found {len(preferred_triples)} preferred triples")
                if preferred_triples:
                    candidate_triples = preferred_triples
                if not candidate_triples:
                    print("No more connected triples found, but not all triples represented.")
                    print(f"Represented: {len(self.represented_triples)}, Total: {len(self.all_triples)}")
                    break

                # choosing triple with least common predicate 
                # min_frequency = float('inf')
                # new_triple = None
                # for triple in candidate_triples:
                #     predicate = triple[1]
                #     frequency = triple_element_frequencies[1][predicate]
                #     if frequency < min_frequency:
                #         min_frequency = frequency
                #         new_triple = triple
            
                new_triple = random.choice(candidate_triples)

                s, p, o = new_triple

                node_new_triple_counts[s] += 1
                node_new_triple_counts[p] += 1
                node_new_triple_counts[o] += 1
                
                # Add the new triple pattern
                class_triple, var_triple = self.get_triple_class_info(new_triple)
                self.b_schema_triples.append((class_triple, var_triple))
                self.b_schema_set.add((class_triple.s, class_triple.p, class_triple.o))
                print(f"Added triple: {new_triple}")
                print(f"Class pattern: ({class_triple.s}, {class_triple.p}, {class_triple.o})")
            
            # Step 2: Invert to SPARQL CONSTRUCT query and execute
            pattern_query = PatternQuery(self.b_schema_triples, self.data_graph)
            construct_query = pattern_query.get_construct_query()
            self.pattern_query = pattern_query
            print('WHERE: ', pattern_query.where)
            # print(f"\nCONSTRUCT Query:\n{construct_query}\n")
            # print("\n Getting Count of triples returned by query: ", list(self.data_graph.query(pattern_query.get_query()))[0][0].toPython())

            result_graph = self.data_graph.query(construct_query).graph
            self.represented_triples = result_graph

            for s,p,o in self.represented_triples:
                node_counts[s] += 1
                node_counts[p] += 1
                node_counts[o] += 1
            
            represented = 0 
            for s, p, o in self.all_triples:
                if (s, p, o) in self.represented_triples:
                    represented += 1

            
            print(f"Triples represented: {represented}/{len(self.all_triples)}")
            
            # Step 3: Check if all triples are represented
            if represented >= (threshold * len(self.all_triples)):
                print("\n" + "="*60)
                print("SUCCESS: All triples represented! Algorithm complete.")
                print("="*60)
                break
        
            if step >= max_iterations:
                pprint(f"\nReached maximum iterations ({max_iterations})")
                pprint(f"\nNodes Present in Representation ({node_counts})")
                pprint(f"\nNodes selected as new triples ({node_new_triple_counts})")
        
        return self.b_schema_triples, pattern_query

import rdflib
from rdflib import Graph, URIRef, Literal
from collections import Counter

def count_nodes(graph: Graph) -> (Counter, Counter, Counter):
    """
    Counts the frequency of each subject, predicate, and object in an rdflib graph.

    Args:
        graph: An rdflib.Graph object.

    Returns:
        A tuple of three collections.Counter objects:
        (subject_counts, predicate_counts, object_counts)
    """
    subject_counts = Counter()
    predicate_counts = Counter()
    object_counts = Counter()
    
    # Iterate through every triple in the graph
    for s, p, o in graph:
        subject_counts[s] += 1
        predicate_counts[p] += 1
        object_counts[o] += 1
        
    return subject_counts, predicate_counts, object_counts


# Helper functions
def get_prefixes(graph):
    """Generate prefix declarations from graph namespaces"""
    if graph is None:
        return ""
    prefixes = []
    for prefix, namespace in graph.namespaces():
        if prefix:  # Skip empty prefix
            prefixes.append(f"PREFIX {prefix}: <{namespace}>")
    return "\n".join(prefixes)

def clean_var_name(var_name):
    return var_name.replace(".", "")#replace("_", "").replace("-", "")
def convert_to_prefixed(uri, graph):
    """Convert URI to prefixed form if possible"""
    if graph is None:
        return f"<{uri}>"
    
    uri_str = str(uri)
    for prefix, namespace in graph.namespaces():
        namespace_str = str(namespace)
        if uri_str.startswith(namespace_str):
            local_name = uri_str[len(namespace_str):]
            if prefix:
                return f"{prefix}:{local_name}"
    return f"<{uri}>"


data_graph = Graph(store="Oxigraph")
data_graph.parse("brick-example.ttl", format="turtle")
algorithm = BSchemaAlgorithm(data_graph)
b_schema, final_query = algorithm.run(150)




# cd /Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/from-data-graph; . ../.venv/bin/activate; python algo-testing.py