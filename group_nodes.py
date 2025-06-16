# %%
from typing import Union
from dataclasses import dataclass
from pyoxigraph import *
from namespaces import *
from rdflib import Graph, URIRef
from collections import defaultdict
from itertools import combinations
import pandas as pd
import numpy as np
from IPython.display import display
import networkx as nx

# 1 (test-graph) and 5 (test-graph5) may be best
TEST_GRAPH_FILE = "test-graphs/test-graph.ttl"
# TEST_GRAPH_FILE = "test-graphs/test-graph5.ttl"
SCHEMA_GRAPH_FILE = "test-graphs/223p.ttl"

g = Graph(store="Oxigraph")
g.parse(TEST_GRAPH_FILE, format="turtle")
EX = Namespace("urn:example#")

prefixes = get_prefixes(g)

store = Store()
odg = NamedNode("urn:original-data-graph")
dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")
store.load(path=TEST_GRAPH_FILE, format=RdfFormat.TURTLE, to_graph=odg)
store.load(path=SCHEMA_GRAPH_FILE, format=RdfFormat.TURTLE, to_graph=sg)


@dataclass(frozen=True)
class Triple:
    s: Union[str, list]
    p: Union[str, list]
    o: Union[str, list]


def get_local_name(node):
    node = str(node).replace("<", "").replace(">", "")
    if "#" in node:
        return node.rpartition("#")[-1]
    else:
        return node.rpartition("/")[-1]


def check_ns(node, ns=S223):
    return get_local_name(node) == str(node).replace(str(ns), "").replace(
        "<", ""
    ).replace(">", "")


def counter(start: int = 0, step: int = 1):
    current = start
    while True:
        yield current
        current += step


count_generator = counter()


def get_class(node, store=store, prefixes=prefixes, ns=S223, ns_prefix="s223:"):

    query = f"""
    {prefixes}
    # PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class WHERE {{
        {str(node)} a ?class . 
        FILTER NOT EXISTS {{
            {str(node)} a ?subclass .
            ?subclass rdfs:subClassOf ?class .
        }}
        FILTER(STRSTARTS(STR(?class), str({ns_prefix})))
    }} """
    classes = list(store.query(query, use_default_graph_as_union=True))
    if len(classes) == 0:
        return None
    return classes[0]["class"].value


def shorten_graph(
    store=store,
    prefixes=prefixes,
    dg=dg,
    odg=odg,
    ns_prefix="s223:",
    exempt_predicates=["s223:cnx", "rdf:type"],
):
    # shortens original data graph (odg) and puts into new named graph called dg
    pred_filters = """
        """.join(
        [f"FILTER(?p != {predicate} )" for predicate in exempt_predicates]
    )
    query = f"""
    {prefixes}
    CONSTRUCT {{
        ?s ?p ?o
        }} 
        WHERE {{  
        ?s ?p ?o . 
        {pred_filters}
        FILTER(STRSTARTS(STR(?p), str({ns_prefix})))
    }} """
    for r in store.query(query, default_graph=[odg]):
        s_class = get_class(r.subject)
        o_class = get_class(r.object)
        if o_class:
            store.add(Quad(r.subject, r.predicate, r.object, dg))
            store.add(Quad(r.subject, NamedNode(A), NamedNode(s_class), dg))
            store.add(Quad(r.object, NamedNode(A), NamedNode(o_class), dg))


class PatternQuery:
    def __init__(self, triples, graph=g):
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
            for var_1, var_2 in combinations(var_list, 2):
                filter_lst.append(f"FILTER (?{var_1} != ?{var_2}) .")

        return "\n".join(filter_lst)

    def make_var_names(self, triples):
        # makes a dictionary with triples of classes to triples with var names
        """
        Makes a dictionary with triples of classes to triples with var names
        :param triples: a list of tuples, where each tuple contains a triple of classes and a triple of variables
        :return: a list of tuples, where each tuple contains a triple of classes and a triple of variables with var names
        """
        counter = {}
        query_triples = []
        for class_triple, var_triple in triples:
            # Also replace dashes?
            subject = get_local_name(var_triple.s).replace("-", "_")
            object = get_local_name(var_triple.o).replace("-", "_")
            # have to remove angle brackets from predicate
            if class_triple.p.startswith("<"):
                p_var = class_triple.p.split("<")[1].split(">")[0]
            else:
                p_var = class_triple.p
            query_triples.append((class_triple, Triple(subject, p_var, object)))
        return query_triples

    # query fragments can be list, then list can be continuously concatenated with fragments. fragments can be joined by '\n'
    def add_where(self, query_triples):
        where = []
        for klass, var in query_triples:
            where.append(f"?{var.s} a {convert_to_prefixed(klass.s,g)} .")
            where.append(f"?{var.s} {convert_to_prefixed(URIRef(var.p),g)} ?{var.o} .")
            where.append(f"?{var.o} a {convert_to_prefixed(klass.o, g)} .")
        return "\n".join(where)

    def get_query(self):
        # may need to add prefixes
        query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {self.where}\n{self.filters} }}"""
        return query


def get_triples(store=store, graph_name=dg):
    triples = []
    for quad in list(store.quads_for_pattern(None, None, None, graph_name)):
        if not check_ns(quad.predicate):
            continue
        s_class = get_class(str(quad.subject))
        if s_class is None:
            continue
        o_class = get_class(str(quad.object))
        if o_class is None:
            continue
        triples.append(
            (
                Triple(str(s_class), str(quad.predicate), str(o_class)),
                Triple(str(quad.subject), str(quad.predicate), str(quad.object)),
            )
        )
    return triples


def find_overlap_columns(df):
    """
    Check if any two columns in a DataFrame have the same value counts.

    Parameters:
    df (pandas.DataFrame): The DataFrame to check

    Returns:
    list: Pairs of column names that have identical value counts
    """
    result = []

    # Get all possible pairs of columns
    column_pairs = list(combinations(df.columns, 2))

    for col1, col2 in column_pairs:
        # Get value counts for both columns
        counts1 = df[col1].value_counts().sort_index()
        counts2 = df[col2].value_counts().sort_index()

        # Check if they have the same indices (values)
        if not counts1.index.equals(counts2.index):
            continue

        # Check if the counts are the same
        if not counts1.equals(counts2):
            continue

        # check if the columns are identical
        if np.array_equal(df[col1], df[col2]):
            # print('columns are identical')
            continue

        result.append((col1, col2))
    # get unpaired columns
    unpaired = []
    for col in df.columns:
        if col not in [c1 for c1, c2 in result] and col not in [
            c2 for c1, c2 in result
        ]:
            unpaired.append(col)

    return result, unpaired


# %%
def find_cycles(pairs):
    G = nx.Graph()
    G.add_edges_from(pairs)
    cycles = list(nx.simple_cycles(G))

    return cycles


def find_sets_from_pairs(pairs):
    cycles = find_cycles(pairs)
    # Convert to tuples for hashability
    pair_tuples = [tuple(lst) for lst in pairs]
    check_set = set(pair_tuples)

    for cycle in cycles:
        cycle_tuple_set = set(combinations(cycle, 2))
        intersection = check_set.intersection(cycle_tuple_set)
        if intersection:
            check_set -= intersection

    groups = list(check_set)
    return groups + [tuple(cycle) for cycle in cycles]


def find_sets(query, store, default_graph):
    print("running query")
    import time

    st = time.time()
    res = store.query(query, default_graph=[default_graph])
    print("getting results to list")
    res_list = list(res)
    print("converting to dataframe")
    df = pd.DataFrame(res_list, columns=res.variables).map(get_local_name)
    et = time.time()
    print(f"took {et-st} seconds")
    print("finding overlapped columns")
    pairs, unpaired = find_overlap_columns(df)
    print("finding sets from pairs")
    groups = find_sets_from_pairs(pairs)
    return groups + unpaired


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
                        new_graph_triples.append(
                            (
                                Triple(class_triple.s, triple.p, class_triple.o),
                                Triple(s_set, triple.p, o_set),
                            )
                        )
    return new_graph_triples


def group_serialization(group, var_replacement=""):
    return "_".join(str(var).replace("?", var_replacement) for var in group)


def create_new_graph(triples, ns=EX):
    # ns is the namespace for the new graph - also used to name the graph
    # create a new graph with the triples
    # serialize groups
    group_dict = {}
    for class_triple, triple in triples:
        s = group_serialization(triple.s)
        o = group_serialization(triple.o)
        group_dict[s] = triple.s
        group_dict[o] = triple.o
        store.add(
            Quad(NamedNode(ns[s]), NamedNode(triple.p), NamedNode(ns[o]), NamedNode(ns))
        )
        store.add(
            Quad(
                NamedNode(ns[s]), NamedNode(A), NamedNode(class_triple.s), NamedNode(ns)
            )
        )
        store.add(
            Quad(
                NamedNode(ns[o]), NamedNode(A), NamedNode(class_triple.o), NamedNode(ns)
            )
        )
    return group_dict


def run():
    print("getting triples")
    groups = get_triples()
    print("building query")
    p = PatternQuery(groups)
    query = p.query
    # print(p.where)
    # res = store.query(p.query, default_graph = [dg])
    # df = pd.DataFrame(list(res), columns = res.variables).map(get_local_name)
    sets = find_sets(query, store, dg)
    return p, sets


def run_for_groups(p, sets):
    # ns is new graph namespace
    ns_str = dg.value + str(next(count_generator)) + "#"
    ns = Namespace(ns_str)
    print("getting_relations")
    new_graph_triples = get_group_relations(p.query_dict, sets)
    print("completed getting relations")
    group_dict = create_new_graph(new_graph_triples, ns)
    groups = get_triples(graph_name=NamedNode(ns))

    p = PatternQuery(groups)
    query = p.query
    # res = store.query(p.query, default_graph = [NamedNode(ns)])
    # df = pd.DataFrame(list(res), columns = res.variables).map(get_local_name)
    sets = find_sets(query, store, NamedNode(ns))
    return p, sets, group_dict


def run_to_completion():
    group_dicts = []
    all_sets = []
    all_p = []
    p, sets = run()
    all_sets.append(sets)
    all_p.append(p)
    while True:
        p, sets, group_dict = run_for_groups(p, sets)
        print("set length ", len(sets))
        print("last set length", len(all_sets[-1]))
        if len(sets) == len(all_sets[-1]):
            break
        else:
            group_dicts.append(group_dict)
            all_sets.append(sets)
            all_p.append(p)
    return all_p, all_sets, group_dicts


from private.visualize_triples import visualize_triples

# %%
shorten_graph(exempt_predicates=[])
store.dump(
    "vrf-cut-short.ttl", format=RdfFormat.TURTLE, from_graph=dg, prefixes=namespace_dict
)
all_p, all_sets, group_dicts = run_to_completion()
display(all_sets)
display(group_dicts)
for p in all_p:
    triples = [triples for _, triples in p.query_dict]
    visualize_triples(triples)
# visualize_last_group
p, sets, group_dict = run_for_groups(all_p[-1], all_sets[-1])
triples = [triples for _, triples in p.query_dict]
a = visualize_triples(triples)
# group_relations = get_group_relations(p.query_dict, all_sets[-1])
# triples = [triples for _, triples in group_relations]
# visualize_triples([triples for _, triples in group_relations])
