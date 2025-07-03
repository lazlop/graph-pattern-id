#%%
from group_nodes import * 
TEST_GRAPH_FILE = "examples/brick-example.ttl"
SCHEMA_GRAPH_FILE = "examples/Brick.ttl"

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


# %%
shorten_graph(store = store, ns = BRICK)
store.dump(
    "brick-short.ttl", format=RdfFormat.TURTLE, from_graph=dg, prefixes=namespace_dict
)
all_p, all_sets, group_dicts = run_to_completion(store = store, schema_ns = BRICK)
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

# %%