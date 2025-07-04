from rdflib import Namespace, URIRef, RDFS
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library
from buildingmotif.namespaces import BMOTIF, BRICK
from buildingmotif.model_builder import TemplateBuilderContext
BLDG = Namespace("urn:example#")
bm = BuildingMOTIF("sqlite://", "topquadrant")
bldg = Model.create("urn:example#")
bldg.graph.bind('',BLDG)
brick = Library.load(ontology_graph="examples/Brick.ttl")
brick_tmpl = Library.load(directory='examples/brick-templates')
import time

from group_nodes import * 

import csv
filename = 'timetesting.csv'

# Writing to CSV
with open(filename, mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=['graph_size','vav_amt','compressed_size', 'time'])
    writer.writeheader()

for j in range(40):
    csv_row = {}
    csv_row['vav_amt'] = j
    ctx = TemplateBuilderContext(BLDG)
    ctx.add_templates_from_library(brick)
    ctx.add_templates_from_library(brick_tmpl)

    bldg_config = {'ahus': 1, 'cv': j, 'hv': 0}
    bldg_ctx_dict = {}
    for i in range(bldg_config['ahus']):
        ahu_name = f'ahu_{i}'
        # bldg_ctx_dict[name] = ctx['multiple-zone-ahu'](name=name)
        ahu = ctx['multiple-zone-ahu'](name=ahu_name)
        for cv in range(bldg_config['cv']):
            cv_name = f'cvav_{i}_{cv}'
            cvav = ctx['vav-cooling-only'](name=cv_name)
            ctx['feeds'](name = ahu['name'], target = cvav['name'])
        for hv in range(bldg_config['hv']):
            hv_name = f'hvav_{i}_{hv}'
            hvav = ctx['vav-with-reheat'](name=hv_name)
            ctx['feeds'](name = ahu['name'], target = hvav['name'])

    bldg.add_graph(ctx.compile())
    bldg.graph.serialize('brick-example.ttl', format = 'ttl')
    csv_row['graph_size'] = len(bldg.graph)

    start_time = time.time()

    TEST_GRAPH_FILE = 'brick-example.ttl'
    SCHEMA_GRAPH_FILE = 'examples/Brick.ttl'
    processor = GraphPatternProcessor(test_graph_file=TEST_GRAPH_FILE, 
                    schema_graph_file=SCHEMA_GRAPH_FILE, 
                    namespace=BRICK)

    # Process and visualize
    all_p, all_sets, group_dicts = processor.process_and_visualize(exempt_predicates=[])
    
    csv_row['compressed_size'] = len(group_dicts[-1])
    end_time = time.time()
    elapsed_time = end_time - start_time
    csv_row['time'] = elapsed_time
    with open(filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['graph_size', 'vav_amt', 'compressed_size', 'time'])
        writer.writerow(csv_row)
