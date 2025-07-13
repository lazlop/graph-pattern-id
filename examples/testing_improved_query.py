#%% 
from rdflib import Namespace, URIRef, RDFS, Graph, Literal
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library
from buildingmotif.namespaces import BMOTIF, BRICK, A, RDF
from buildingmotif.model_builder import TemplateBuilderContext
from time import time
import sys
import os
# current_dir = os.path.dirname(__file__)
# utils_path = os.path.abspath(os.path.join(current_dir, '..', 'utils'))
sys.path.insert(0, '../utils')
from utils import query_to_df, get_prefixes
# %%
BLDG = Namespace("urn:example#")
bm = BuildingMOTIF("sqlite://", "topquadrant")
bldg = Model.create("urn:example#")
bldg.graph.bind('',BLDG)
brick = Library.load(ontology_graph="Brick.ttl")

# %%
brick_tmpl = Library.load(directory='brick-templates')

ctx = TemplateBuilderContext(BLDG)
ctx.add_templates_from_library(brick)
ctx.add_templates_from_library(brick_tmpl)

def get_wrapper_dict(ctx):
    wrapper_dict = {}
    for wrapper in ctx.wrappers:
        if wrapper.template.name not in wrapper_dict.keys():
            wrapper_dict[wrapper.template.name] = [wrapper]
        else:
            wrapper_dict[wrapper.template.name].append(wrapper)
    return wrapper_dict

# %%
wrapper_dict = get_wrapper_dict(ctx)
template_types = wrapper_dict.keys()
print(template_types)

# %%
not_condensed_t = []
condensed_t = []
model_length = []
for n in range(20):
    bldg = Model.create("urn:example#")
    bldg.graph.bind('',BLDG)
    g = Graph(store = 'Oxigraph')
    g.bind('',BLDG)

    bldg_config = {'ahus': 1+n, 'cv': 15, 'hv': 15}
    bldg_ctx_dict = {}
    for i in range(bldg_config['ahus']):
        if i<n:
            continue
        template_name = 'multiple-zone-ahu'
        ahu_name = f'ahu_{i}'
        ahu = ctx[template_name](name=ahu_name)
        ahu.bindings = {k: BLDG[f"{template_name}_{k}_{i}"] for k in ahu.parameters}
        # display(ahu.bindings)
        # also adding to condensed representation 
        for k,v in ahu.bindings.items():
            # g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDF[f"_{i+1}"], v))
            g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDFS[f"member"], v))
        for cv in range(bldg_config['cv']):
            template_name = 'vav-cooling-only'
            cv_name = f'cvav_{i}_{cv}'
            cvav = ctx[template_name](name=cv_name)
            cvav.bindings = {k: BLDG[f"{template_name}_{k}_{i}_{cv}"] for k in cvav.parameters}
            ctx['feeds'](name = ahu['name'], target = cvav['name'])
            for k,v in cvav.bindings.items():
                # g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDF[f"_{cv+1}"], v))
                g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDFS[f"member"], v))
            # print(cvav.bindings)
        for hv in range(bldg_config['hv']):
            template_name = 'vav-with-reheat'
            hv_name = f'hvav_{i}_{hv}'
            hvav = ctx[template_name](name=hv_name)
            hvav.bindings = {k: BLDG[f"{template_name}_{k}_{i}_{hv}"] for k in hvav.parameters}
            ctx['feeds'](name = ahu['name'], target = hvav['name'])
            for k,v in hvav.bindings.items():
                # g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDF[f"_{hv+1}"], v))
                g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDFS[f"member"], v))

    if n < 1:
        wrapper_dict = get_wrapper_dict(ctx)
        template_types = wrapper_dict.keys()

    if n < 1:
        skip_templates = ['feeds']
        print(skip_templates)
        for tp in template_types:
            if tp in skip_templates:
                continue
            for wrapper in wrapper_dict[tp]:
                params = wrapper.parameters
                eval_dict = {}
                for param in params:
                    # if param not in TEMPLATE_PARAMS_COMPILED[tp].keys():
                    #     print(param)
                    # g.add((BLDG[f"{tp}-{param.replace('name-','')}"], A, BRICK[TEMPLATE_PARAMS_COMPILED[tp][param]]))
                    name = f"{tp}-{param.replace('name-','')}"
                    g.add((BLDG[name], A, RDF.Seq))
                    eval_dict[param] = BLDG[name]
                template_graph = wrapper.template.evaluate(eval_dict)
                if not isinstance(template_graph, Graph):
                    print('not a graph, cant add')
                g = g + template_graph
            # adding feeds manually 
            g.add((BLDG['multiple-zone-ahu-name'], BRICK.feeds, BLDG['vav-cooling-only-name']))
            g.add((BLDG['multiple-zone-ahu-name'], BRICK.feeds, BLDG['vav-with-reheat-name']))
    
    bldg.add_graph(ctx.compile())
    # print(len(g))
    # print(len(bldg.graph))

    bldg_graph = Graph(store = 'Oxigraph')
    for s,p,o in bldg.graph.triples((None,None,None)):
        bldg_graph.add((s,p,o))
    for s,p,o in g.triples((None,None,None)):
        bldg_graph.add((s,p,o))
    st = time()

    group_bldg_query_wrong = """
    SELECT ?dat ?vav ?ahu
    WHERE {
        ?dat a brick:Discharge_Air_Temperature_Sensor .
        ?vav a brick:VAV .
        ?vav brick:hasPoint ?dat .
        ?ahu brick:feeds ?vav
        FILTER NOT EXISTS {
            ?vav brick:hasPart ?rc .
            ?rc a brick:Heating_Coil .
        }
    }
    """
    query_to_df(group_bldg_query_wrong, bldg_graph)
    not_condensed_t.append(time() - st)

    st = time()
    group_bldg_query = """
    SELECT ?dat ?vav ?ahu
    WHERE {
        ?vavC a brick:VAV .
        ?vavC rdfs:member ?vav .
        ?ahu brick:feeds ?vav .
        ?vav brick:hasPoint ?dat .
        ?dat a brick:Discharge_Air_Temperature_Sensor .
        FILTER NOT EXISTS {
            ?vavC brick:hasPart ?rc .
            ?rc a brick:Heating_Coil .
        }
    }
    """
    query_to_df(group_bldg_query, bldg_graph)
    condensed_t.append(time() - st)
    # breaking at 5 minutes
    model_length.append(len(bldg_graph))
    if not_condensed_t[-1] >= 600:
        break 
# %%
import csv
# Combine arrays into a list of rows
rows = [model_length, not_condensed_t, condensed_t]
import matplotlib.pyplot as plt
import pandas as pd 
df = pd.DataFrame({
    'model_length': model_length,
    'not_condensed_t': not_condensed_t,
    'condensed_t': condensed_t
})
df.to_csv('query-time-s223.csv')
plt.ylabel('Query Time (seconds)')
plt.plot([f"{n/1000}k" for n in model_length],not_condensed_t, label='Without Condensed Representation')
plt.plot([f"{n/1000}k" for n in model_length],condensed_t, label='With Condensed Representation')
plt.xlabel('Size of Model (1000s of triples)')
# plt.xticks(model_length, [f'{1+i} [{x}]' for i,x in enumerate(model_length)])
plt.legend()
plt.savefig('query-time.png')
