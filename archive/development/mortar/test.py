"""
Notes:
for mortar bldg1, iri parsing fails...  
"""
import sys 
sys.path.append('../../../utils')
from algo2 import * 
data_graph = Graph(store = 'Oxigraph')
data_graph.parse("buildings/bldg1.ttl", format="turtle")

algo = BSchemaGenerator(data_graph)
b_schema_statements = algo.generate_b_schema()
print(b_schema_statements)
b_schema_trpls = [stmt.pattern[0][1] for stmt in b_schema_statements]
b_schema_graph = Graph(store = 'Oxigraph')
for trpl in b_schema_trpls:
    b_schema_graph.add((trpl.s, trpl.p, trpl.o))
b_schema_graph.serialize("bschema/bldg1.ttl", format="turtle")