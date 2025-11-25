#!/usr/bin/env python
import argparse
from rdflib import Graph
from .bschema import create_bschema, bind_prefixes
import os

def run():
    parser = argparse.ArgumentParser(description='Create the bschema for a given .ttl file')
    parser.add_argument('-i', '--input_file', required=True, help='Path to the input RDF file')
    parser.add_argument('-o', '--output_file', help='Path to the output RDF file')
    parser.add_argument('-t', '--threshold', type=float, help='Similarity threshold, lower thresholds let groupings with not the exact same representation be grouped together(try 0.5)')
    parser.add_argument('-d', '--delete_added_classes', action='store_true', help='Delete added classes')
    parser.add_argument('-r', '--iterations', type=int, default=10, help='Number of iterations')

    args = parser.parse_args()

    data_graph = Graph(store='Oxigraph')
    data_graph.parse(args.input_file)

    cg, mg, i = create_bschema(data_graph, args.iterations, args.threshold, args.delete_added_classes)

    bind_prefixes(cg)

    if args.output_file is None:
        base, extension = os.path.splitext(args.input_file)
        if args.threshold is not None:
            output_file = f"{base}_threshold_{args.threshold}_bschema{extension}"
        else:
            output_file = f"{base}_bschema{extension}"
    else:
        output_file = args.output_file

    cg.serialize(output_file)

    print(f"Compressed to {len(cg) / len(data_graph) * 100:.2f}% of its original size")

if __name__ == "__main__":
    run()