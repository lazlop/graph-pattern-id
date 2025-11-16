"""
NOTE: Routinely hitting max iterations even with low required similarity thresholds. Would be good to discover why. 
The amount of max iterations is related to the shortest length between a distinguishing characteristic and another class. In these graphs that shortest distance could possibly be larger than 10 (though it is surprising that it seems to be higher than 10 for all of them)
"""

import os 
import sys 
sys.path.append('../../')
from utils import *
from algorithm.main import * 
import matplotlib.pyplot as plt

def get_mortar_graphs(directory_path):
    g = Graph(store = "Oxigraph")
    for file_name in os.listdir(directory_path):
        # if file_name != 'bldg1.ttl':
        #     continue
        if file_name.endswith(".ttl"):
            file_path = os.path.join(directory_path, file_name)
            print(f"Processing file: {file_name}")
            try:
                g.parse(file_path, format="turtle")
            except Exception as e:
                print(f"Error parsing {file_name}: {e}")
        yield file_name, g


if __name__ == "__main__":
    directory_path = "from-website"
    gs = []
    cgs = []
    file_names = []
    threshold = 0.5
    i = 0 
    # TODO: see what it looks like removing labels and stuff like that. 
    for file_name, g in get_mortar_graphs(directory_path):
        gs.append(g)
        file_names.append(file_name)
        cg, mg = run_algo(g, iterations=2,similarity_threshold=threshold)
        # removing extraneous classes
        for s,p,o in cg:
            if (p == A) & (str(HPFS) in str(o)):
                cg.remove((s,p,o))
        cg.serialize('bschema/'+ f'theshold{threshold}' + file_name, format="turtle")
        cgs.append(cg)
        print("compressed to ", len(cg)/len(g)*100, "% of its original size")
        # cg.print()
        if i >= 2:
            break
        i += 1
    # size of original graph vs size of compressed graph 
    plt.plot([len(g) for g in gs], [len(cg) for cg in cgs], 'o')
    plt.savefig("mortar_graph_sizes.png")