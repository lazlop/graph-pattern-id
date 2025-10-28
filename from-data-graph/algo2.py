from pprint import pprint
from typing import Union, List, Union, Tuple, Optional
from matplotlib import pyplot as plt
import time 
from dataclasses import dataclass
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
from namespaces import *
from utils import * 
from dataclasses import dataclass
from typing import Union, Set
from collections import defaultdict
from itertools import combinations
from rdflib import URIRef, Graph
import random

from dataclasses import dataclass
from typing import Union, Set, List, Tuple, Dict
from collections import defaultdict
from rdflib import URIRef, Graph
from itertools import combinations
# Implementation doesn't reqlly catch all the triples in a graph, especially things without classes or that may be unconnected


@dataclass(frozen=True)
class Triple:
    s: Union[str, URIRef]
    p: Union[str, URIRef]
    o: Union[str, URIRef]

# TODO: Should probably move from typle of triples to a better data structure
# @dataclass(frozen=True)
# class BSchemaTriple:
#     classes: Triple 
#     vars: Triple


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
        query = f"""{self.prefixes}\nCONSTRUCT {{\n{self.where}\n}} WHERE {{\n{self.where}\n}} LIMIT 1"""
        return query
    
    def get_ask_query(self):
        query = f"""{self.prefixes}\nASK WHERE {{ {self.where}\n}} LIMIT 1"""
        return query
@dataclass
class BSchemaStatement:
    """Represents a statement in the b-schema with its pattern and covered triples"""
    pattern: List[Tuple[Triple, Triple]]  # (class_triple, var_triple) pairs
    covered_triples: Set[Triple]
    
    def __init__(self, pattern):
        self.pattern = pattern
        self.covered_triples = set()
    
    def __repr__(self):
        """Better representation for debugging"""
        pattern_str = "\n  ".join([f"{ct} -> {vt}" for ct, vt in self.pattern])
        return f"BSchemaStatement(\n  Pattern:\n  {pattern_str}\n  Covers {len(self.covered_triples)} triples\n)"

class BSchemaGenerator:
    def __init__(self, data_graph: Graph):
        self.data_graph = data_graph
        self.b_schema_statements: List[BSchemaStatement] = []
        self.all_triples = self._extract_all_triples()
        self.covered_triples: Set[Triple] = set()
        
        print(f"[INIT] Total triples in graph: {len(self.all_triples)}")
        
    def _extract_all_triples(self) -> List[Triple]:
        """Extract all triples from the data graph"""
        triples = []
        for s, p, o in self.data_graph:
            triples.append(Triple(s, p, o))
        print(f"[EXTRACT] Extracted {len(triples)} triples")
        return triples
    
    def _get_triples_same_subject_object(self, triple: Triple) -> List[Triple]:
        """Get all triples with the same subject and object as the given triple"""
        same_so_triples = [triple]
        for t in self.all_triples:
            if t != triple and t.s == triple.s and t.o == triple.o:
                same_so_triples.append(t)
        
        # print(f"[SAME_SO] Found {len(same_so_triples)} triples with same subject/object as {triple.p}")
        return same_so_triples
    
    def _get_class(self, node: URIRef) -> URIRef:
        """Get the class of a node from the data graph"""
        A = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        for _, _, o in self.data_graph.triples((node, A, None)):
            return o
        # Default to rdfs:Resource if no type found
        return URIRef("http://www.w3.org/2000/01/rdf-schema#Resource")
    
    def _create_class_pattern(self, triples: List[Triple]) -> List[Tuple[Triple, Triple]]:
        """Create class-based pattern from concrete triples"""
        pattern = []
        var_counter = {}
        
        for triple in triples:
            # Get classes
            s_class = self._get_class(triple.s)
            o_class = self._get_class(triple.o)
            
            # Create variable names
            s_var = self._get_or_create_var(triple.s, var_counter)
            o_var = self._get_or_create_var(triple.o, var_counter)
            
            class_triple = Triple(str(s_class), str(triple.p), str(o_class))
            var_triple = Triple(s_var, triple.p, o_var)
            
            pattern.append((class_triple, var_triple))
        
        print(f"[PATTERN] Created pattern with {len(pattern)} triples")
        for ct, vt in pattern:
            print(f"  {ct.s} --{ct.p}--> {ct.o}")
        
        return pattern
    
    def _get_or_create_var(self, node: URIRef, var_counter: Dict) -> str:
        """Create or retrieve variable name for a node"""
        if node not in var_counter:
            var_counter[node] = node  # Store the actual node for variable naming
        return node
    
    def _find_connected_triple(self) -> Triple:
        """Find a triple connected to existing b-schema but not yet covered"""
        if not self.b_schema_statements:
            return None
        
        # Get all nodes in the current b-schema
        schema_nodes = set()
        for stmt in self.b_schema_statements:
            for t in stmt.covered_triples:
                schema_nodes.add(t.s)
                schema_nodes.add(t.o)
        
        # print(f"[CONNECT] Schema has {len(schema_nodes)} unique nodes")
        
        # Find uncovered triple connected to schema
        for triple in self.all_triples:
            if triple not in self.covered_triples:
                if triple.s in schema_nodes or triple.o in schema_nodes:
                    print(f"[CONNECT] Found connected triple: {triple.s} --{triple.p}--> {triple.o}")
                    return triple
        
        # print(f"[CONNECT] No connected triple found")
        return None
    
    def _find_candidate_statements(self, new_triples: List[Triple]) -> List[BSchemaStatement]:
        """Find candidate b-schema statements that may represent the new triples"""
        candidates = []
        
        # Get class pattern of new triples
        new_pattern = self._create_class_pattern(new_triples)
        
        # print(f"[CANDIDATES] Checking {len(self.b_schema_statements)} existing statements")
        
        for i, stmt in enumerate(self.b_schema_statements):
            # print(f"  [CANDIDATES] Checking statement {i}...")
            # Check if patterns match (same classes and relations)
            if self._patterns_compatible(stmt.pattern, new_pattern):
                # print(f"    [CANDIDATES] Statement {i} is COMPATIBLE")
                candidates.append(stmt)
            else:
                # print(f"    [CANDIDATES] Statement {i} is NOT compatible")
                pass
        
        print(f"[CANDIDATES] Found {len(candidates)} candidate statements")
        return candidates
    
    def _patterns_compatible(self, pattern1, pattern2) -> bool:
        """Check if two patterns have compatible classes and relations"""
        if len(pattern1) != len(pattern2):
            print(f"    [COMPAT] Length mismatch: {len(pattern1)} vs {len(pattern2)}")
            return False
        
        # ISSUE: You're comparing var_triples instead of class_triples!
        # The var_triples contain the actual URIs, not the patterns
        # Should compare class patterns (pattern[0] not pattern[1])
        class_patterns1 = {(ct.s, ct.p, ct.o) for ct, vt in pattern1}
        class_patterns2 = {(ct.s, ct.p, ct.o) for ct, vt in pattern2}
        
        # print(f"    [COMPAT] Pattern1 classes: {class_patterns1}")
        # print(f"    [COMPAT] Pattern2 classes: {class_patterns2}")
        
        if class_patterns1 != class_patterns2:
            # print(f"    [COMPAT] Class patterns don't match")
            return False
        
        # print(f"    [COMPAT] Patterns are compatible!")
        return True
    
    def get_local_name(self, node):
        """Helper to get local name from URI"""
        node = str(node).replace("<", "").replace(">", "")
        if "#" in node:
            return node.rpartition("#")[-1]
        else:
            return node.rpartition("/")[-1]
    
    def _bind_triples_to_query(self, query: str, triples: List[Triple], statement: BSchemaStatement) -> str:
        """Bind triples' values to query variables. 
        All triples have the same subject and object, so we only bind once."""
        
        # All triples have same subject and object, so just use the first one
        representative_triple = triples[0]
        
        print(f"[BIND] Binding triple: {representative_triple.s} --{representative_triple.p}--> {representative_triple.o}")
        
        # Get the class patterns of the new triples
        new_patterns = self._create_class_pattern(triples)
        new_class_triples = {pattern[0] for pattern in new_patterns}
        
        # Get statement class triples for comparison
        stmt_class_triples = {pattern[0] for pattern in statement.pattern}
        
        # Find any matching class triple to get the variable names
        s_var = None
        o_var = None
        
        for new_class_triple, new_var_triple in new_patterns:
            for stmt_class_triple, stmt_var_triple in statement.pattern:
                if (stmt_class_triple.s == new_class_triple.s and 
                    stmt_class_triple.p == new_class_triple.p and 
                    stmt_class_triple.o == new_class_triple.o):
                    
                    s_var = clean_var_name(self.get_local_name(stmt_var_triple.s))
                    o_var = clean_var_name(self.get_local_name(stmt_var_triple.o))
                    print(f"[BIND] Found matching pattern, vars: ?{s_var}, ?{o_var}")
                    break
            
            if s_var is not None:
                break
        
        if s_var is None or o_var is None:
            print(f"[BIND] ERROR: Could not find matching pattern for binding!")
            return query  # No matching pattern found
        
        # Create single VALUES clause binding the shared subject and object
        # values_clause = f"VALUES (?{s_var} ?{o_var}) {{ (<{representative_triple.s}> <{representative_triple.o}>) }}"

        # Think I should only bind subjects
        values_clause = f"VALUES (?{s_var}) {{ (<{representative_triple.s}>) }}"
        
        # print(f"[BIND] VALUES clause: {values_clause}")
        
        # Insert VALUES clause into WHERE clause
        where_pos = query.find("WHERE")
        if where_pos != -1:
            insert_pos = query.find("{", where_pos) + 1
            query = query[:insert_pos] + "\n    " + values_clause + "\n" + query[insert_pos:]
        
        # print(f"[BIND] Final query:\n{query}")
        return query

    def _test_triples_against_statement(self, triples: List[Triple], statement: BSchemaStatement) -> bool:
        """Test if a set of triples (with same subject/object) matches a b-schema statement"""
        
        # print(f"\n[TEST] Testing {len(triples)} triples against statement")
        
        # # Verify all triples have same subject and object
        # if not triples:
        #     return False
        
        # first = triples[0]
        # if not all(t.s == first.s and t.o == first.o for t in triples):
        #     raise ValueError("All triples must have the same subject and object")
        
        all_var_triples = []
        for stmt in self.b_schema_statements:
            pattern = stmt.pattern
            for class_var_triple in pattern:
                all_var_triples.append(class_var_triple)
        
        # Create query from statement pattern
        query_obj = PatternQuery(all_var_triples, self.data_graph)

        # base_query = query_obj.get_construct_query()
        base_query = query_obj.get_ask_query()
        
        # print(f"[TEST] Base query:\n{base_query}\n")
        
        # Bind the shared subject and object
        bound_query = self._bind_triples_to_query(base_query, triples, statement)
        
        # Execute query with LIMIT 1
        try:
            results = self.data_graph.query(bound_query)
            result_count = len(results)
            print(f"[TEST] Query returned {result_count} results")
            
            if result_count > 0:
                print(f"[TEST] ✓ MATCH FOUND")
                return True
            else:
                print(f"[TEST] ✗ NO MATCH")
                return False
                
        except Exception as e:
            print(f"[TEST] ✗ Query execution error: {e}")
            print(f"[TEST] Query was: {bound_query}")
            return False
    
    def generate_b_schema(self) -> List[BSchemaStatement]:
        """Main algorithm to generate b-schema"""
        
        print("\n" + "="*80)
        print("STARTING B-SCHEMA GENERATION")
        print("="*80 + "\n")
        
        # Step 1: Start with first triple(s)
        if not self.all_triples:
            return []
        
        # Add first random triple and triples with same subject/object
        first_triple = self.all_triples[0]
        print(f"\n[STEP 1] Starting with first triple: {first_triple.s} --{first_triple.p}--> {first_triple.o}")
        
        initial_triples = self._get_triples_same_subject_object(first_triple)
        
        # Create initial statement
        initial_pattern = self._create_class_pattern(initial_triples)
        initial_stmt = BSchemaStatement(initial_pattern)
        initial_stmt.covered_triples.update(initial_triples)
        self.b_schema_statements.append(initial_stmt)
        self.covered_triples.update(initial_triples)
        
        print(f"\n[STEP 1] Created initial statement covering {len(initial_triples)} triples")
        print(f"[STEP 1] Coverage: {len(self.covered_triples)}/{len(self.all_triples)} triples")
        
        iteration = 0
        # Step 5: Repeat until all triples are covered
        while len(self.covered_triples) < len(self.all_triples):
            iteration += 1
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration}")
            print(f"Coverage: {len(self.covered_triples)}/{len(self.all_triples)} triples")
            print(f"Current statements: {len(self.b_schema_statements)}")
            print(f"{'='*80}\n")
            
            # Step 1 (continued): Find connected triple
            next_triple = self._find_connected_triple()
            if not next_triple:
                # No connected triple found, pick any uncovered triple
                print("[ITERATION] No connected triple, picking any uncovered triple")
                for t in self.all_triples:
                    if t not in self.covered_triples:
                        next_triple = t
                        print(f"[ITERATION] Selected: {t.s} --{t.p}--> {t.o}")
                        break
            
            if not next_triple:
                print("[ITERATION] No more uncovered triples found!")
                break
            
            # Get all triples with same subject/object
            new_triples = self._get_triples_same_subject_object(next_triple)
            new_triples = [t for t in new_triples if t not in self.covered_triples]
            
            if not new_triples:
                print("[ITERATION] All same-subject-object triples already covered, continuing...")
                continue
            
            print(f"\n[STEP 2] Finding candidates for {len(new_triples)} new triples")
            # Step 2: Find candidate statements
            candidates = self._find_candidate_statements(new_triples)
            
            # Step 4: Test triples against candidates
            matched = False
            for i, candidate in enumerate(candidates):
                print(f"\n[STEP 4] Testing against candidate {i}...")
                # Test all new triples at once (they share subject/object)
                if self._test_triples_against_statement(new_triples, candidate):
                    # Add to existing statement
                    print(f"[STEP 4] ✓ Adding {len(new_triples)} triples to existing statement {i}")
                    candidate.covered_triples.update(new_triples)
                    self.covered_triples.update(new_triples)
                    matched = True
                    break
            
            # If no match, create new statement
            if not matched:
                print(f"\n[STEP 4] ✗ No match found, creating NEW statement")
                new_pattern = self._create_class_pattern(new_triples)
                new_stmt = BSchemaStatement(new_pattern)
                new_stmt.covered_triples.update(new_triples)
                self.b_schema_statements.append(new_stmt)
                self.covered_triples.update(new_triples)
                print(f"[STEP 4] Created statement #{len(self.b_schema_statements)}")
            
            print(f"\n[ITERATION END] Coverage: {len(self.covered_triples)}/{len(self.all_triples)} triples")
            print(f"[ITERATION END] Total statements: {len(self.b_schema_statements)}")
        
        print(f"\n{'='*80}")
        print("B-SCHEMA GENERATION COMPLETE")
        print(f"Final statements: {len(self.b_schema_statements)}")
        print(f"Total coverage: {len(self.covered_triples)}/{len(self.all_triples)} triples")
        print(f"{'='*80}\n")
        
        return self.b_schema_statements

# Helper functions from your example code
def clean_var_name(var_name):
    """Clean variable names for SPARQL"""
    return str(var_name).replace("-", "_").replace(":", "_").replace("/", "_").replace("#", "_")

def convert_to_prefixed(uri, graph):
    """Convert URI to prefixed form"""
    # Simplified - you'll need proper namespace handling
    return f"<{uri}>"

def get_prefixes(graph):
    """Get SPARQL prefixes from graph"""
    prefixes = []
    for prefix, namespace in graph.namespaces():
        prefixes.append(f"PREFIX {prefix}: <{namespace}>")
    return "\n".join(prefixes)

if __name__ == "__main__":
    # Example usage
    data_graph = Graph(store = 'Oxigraph')
    data_graph.parse("brick-example.ttl", format="turtle")
    
    algo = BSchemaGenerator(data_graph)
    b_schema_statements = algo.generate_b_schema()
    
    print("\n" + "="*80)
    print("FINAL B-SCHEMA STATEMENTS:")
    print("="*80)
    for i, stmt in enumerate(b_schema_statements):
        print(f"\nStatement {i}:")
        print(stmt)

    
    b_schema_trpls = [stmt.pattern[0][1] for stmt in b_schema_statements]
    b_schema_graph = Graph(store = 'Oxigraph')
    for trpl in b_schema_trpls:
        b_schema_graph.add((trpl.s, trpl.p, trpl.o))
    b_schema_graph.serialize("b-schema-algo2.ttl", format="turtle")