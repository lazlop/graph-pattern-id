import matplotlib.pyplot as plt
import pandas as pd 

thresh5 = pd.read_csv('lengths_buildingqa50.csv').sort_values(by='graph_length')
full = pd.read_csv('lengths_buildingqa.csv').sort_values(by='graph_length')

g_lens = list(thresh5.graph_length)
cg_lens = list(thresh5.bschema_length)
g_lens2 = list(full.graph_length)
cg_lens2 = list(full.bschema_length)

plt.plot(g_lens, cg_lens, marker = 'o',linestyle = '--', color = 'tab:blue', label = "Partial Similarity")
plt.plot(g_lens2, cg_lens2, marker = '*', color = 'tab:orange', linestyle = '--', label = "BSchema")

plt.xscale('log')

plt.xlabel("Original Graph Size (Triples, Log Scale)")
plt.ylabel("Compressed Graph Size (Triples)")
plt.title(f"BSchema Length By Graph Size")
plt.legend()
plt.savefig("combined_graph_sizes.png")
plt.clf()
plt.plot(g_lens, [(cg_len/g_len) for cg_len, g_len in zip(cg_lens, g_lens)], linestyle = '--', marker =  'o', color = 'tab:blue', label = "Partial Similarity")
plt.plot(g_lens, [(cg_len/g_len) for cg_len, g_len in zip(cg_lens2, g_lens2)], linestyle = '--', marker = '*', color = 'tab:orange', label = "BSchema")

plt.xscale('log')

plt.xlabel("Original Graph Size (Triples, Log Scale)")
plt.ylabel("Compression Ratio (Triples)")
plt.title(f"BSchema Compression Ratio By Graph Size")
plt.legend()
plt.savefig("combined_compression_ratios.png")

print("Weighted Average Compression BSchema: ", sum(cg_lens2)/sum(g_lens2) * 100)
print("Weighted Average Compression Partial Similarity: ", sum(cg_lens)/sum(g_lens) * 100)
print("Average Size of Graph: ", sum(g_lens)/len(g_lens))
print("Average Size of BSchema: ", sum(cg_lens2)/len(cg_lens2))
print("Average Size of Partial Similarity: ", sum(cg_lens)/len(cg_lens))