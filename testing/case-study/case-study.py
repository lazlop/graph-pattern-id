import csv
import os 
import sys 
sys.path.append('../../')
from utils import *
from bschema import * 
import matplotlib.pyplot as plt

data_graph = Graph(store = 'Oxigraph')
data_graph.parse("/Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/archive/development/brick-example.ttl", format="turtle")
s223_data_graph = Graph(store = 'Oxigraph')
s223_data_graph.parse("/Users/lazlopaul/Desktop/223p/experiments/graph-pattern-id/archive/development/s223-example.ttl", format="turtle")
cg, mg = create_bschema(data_graph, 4)
for s,p,o in cg:
    if (p == A) & (str(HPFS) in str(o)):
        cg.remove((s,p,o))
    # if p == RDFS.label:
    #     cg.remove((s,p,o))
bind_prefixes(cg)
cg.serialize('algo5-brick.ttl')
# mg.print()
print("compressed to ", len(cg)/len(data_graph)*100, "% of its original size")
# if PRINT_GRAPHS:
#     cg.print()

cg, mg = create_bschema(s223_data_graph, 5)
for s,p,o in cg:
    if (p == A) & (str(HPFS) in str(o)):
        cg.remove((s,p,o))
    # if p == RDFS.label:
    #     cg.remove((s,p,o))
bind_prefixes(cg)
cg.serialize('algo5-s223.ttl')
print("compressed to ", len(cg)/len(data_graph)*100, "% of its original size")
# if PRINT_GRAPHS:
#     cg.print()
