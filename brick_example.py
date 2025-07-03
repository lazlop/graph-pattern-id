#%%
from group_nodes import * 

TEST_GRAPH_FILE = 'examples/brick-example.ttl'
# TEST_GRAPH_FILE = "test-graphs/test-graph-brick.ttl"
SCHEMA_GRAPH_FILE = 'examples/Brick.ttl'
processor = GraphPatternProcessor(test_graph_file=TEST_GRAPH_FILE, 
                schema_graph_file=SCHEMA_GRAPH_FILE, 
                namespace=BRICK)

# Process and visualize
all_p, all_sets, group_dicts = processor.process_and_visualize(exempt_predicates=[])

# %%
