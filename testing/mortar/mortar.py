"""
NOTE: Routinely hitting max iterations even with low required similarity thresholds. Would be good to discover why. 
The amount of max iterations is related to the shortest length between a distinguishing characteristic and another class. In these graphs that shortest distance could possibly be larger than 10 (though it is surprising that it seems to be higher than 10 for all of them)
"""
import csv
import os 
import sys 
sys.path.append('../../')
from utils import *
from bschema.main import * 
import matplotlib.pyplot as plt

def get_mortar_graphs(directory_path):
    for file_name in os.listdir(directory_path):
        # if file_name != 'bldg1.ttl':
        #     continue
        if file_name.endswith(".ttl"):
            file_path = os.path.join(directory_path, file_name)
            print(f"Processing file: {file_name}")
            try:
                g = Graph(store = "Oxigraph")
                g.parse(file_path, format="turtle")
            except Exception as e:
                print(f"Error parsing {file_name}: {e}")
        yield file_name, g


if __name__ == "__main__":
    directory_path = "from-website"
    gs = []
    cgs = []
    g_lens = []
    cg_lens = []
    file_names = []
    threshold = None
    i = 0 
    # TODO: see what it looks like removing labels and stuff like that. 
    for file_name, g in get_mortar_graphs(directory_path):
        gs.append(g)
        g_lens.append(len(g))
        file_names.append(file_name)
        cg, mg = run_algo(g, iterations=10, similarity_threshold=threshold)
        # removing extraneous classes
        for s,p,o in cg:
            if (p == A) & (str(HPFS) in str(o)):
                cg.remove((s,p,o))
        cg.serialize('bschema/'+ f'theshold{threshold}' + file_name, format="turtle")
        cgs.append(cg)
        print("compressed to ", len(cg)/len(g)*100, "% of its original size")
        # cg.print()
        cg_lens.append(len(cg))
        # if i >= 15:
        #     break
        i += 1
    # size of original graph vs size of compressed graph 
    plt.plot(g_lens, cg_lens, 'o')
    plt.xlabel("Original Graph Size")
    plt.ylabel("Compressed Graph Size")
    plt.title(f"Mortar Building Compression By Graph Size (Threshold: {threshold})")
    plt.savefig("mortar_graph_sizes.png")
    plt.clf()
    plt.plot(g_lens, [(cg_len/g_len) for cg_len, g_len in zip(cg_lens, g_lens)], 'o')
    plt.xlabel("Original Graph Size")
    plt.ylabel("Compression Ratio")
    plt.title(f"Mortar Building Compression Ratio By Graph Size (Threshold: {threshold})")
    plt.savefig("compression_ratios.png")

    with open('lengths.csv', 'w', newline='') as csvfile:
        # Create a CSV writer object
        writer = csv.writer(csvfile)

        # Optionally, write a header row
        writer.writerow(["graph_length", "bschema_length"])

        # Use zip to combine the elements of the two lists into pairs
        # Then, write each pair as a row in the CSV
        for item1, item2 in zip(g_lens, cg_lens):
            writer.writerow([item1, item2])