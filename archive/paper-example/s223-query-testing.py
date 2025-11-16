# %% [markdown]
# # Example Brick Model for process
# Example brick model will be 2 AHUs, 60 terminal units.
# Half are for perimeter zones vavs with reheat, half are for core zones and are cooling only 
# 
# 10 core zone terminal units are for mechanical rooms, networking closets, and electrical rooms that must be served 24/7

# %%
from rdflib import Namespace, URIRef, RDFS, Graph, Literal
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library
from buildingmotif.namespaces import BMOTIF, BRICK, A, RDF, S223
from buildingmotif.model_builder import TemplateBuilderContext
from time import time

# %%
BLDG = Namespace("urn:example#")
bm = BuildingMOTIF("sqlite://", "topquadrant")
bldg = Model.create("urn:example#")
bldg.graph.bind('',BLDG)
bldg.graph.bind('s223',S223)

# %%
brick_tmpl = Library.load(directory='s223-templates')

# %%

ctx = TemplateBuilderContext(BLDG)
ctx.add_templates_from_library(brick_tmpl)

# %%
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
ahu = brick_tmpl.get_template_by_name('multiple-zone-ahu')

# %%
def assemble_ahu(bindings):
    components = ['sa_fan', 'ra_damper', 'clg_coil', 'htg_coil']
    for i in range(1, len(components)): 
        ctx['feeds'](name = bindings[components[i-1]], target = bindings[components[i]])
    # ctx['in-maps-to'](name = bindings['name'], target = bindings[components[0]])
    # ctx['out-maps-to'](name = bindings['name'], target = bindings[components[-1]])


not_condensed_t = []
condensed_t = []
condensed_reasoning_t = []
not_condensed_reasoning_t = []
model_length = []
for n in range(20):
    bldg = Model.create("urn:example#")
    bldg.graph.bind('',BLDG)
    g = Graph(store = 'Oxigraph')
    g.bind('',BLDG)
    g.bind('s223',S223)

    bldg_config = {'ahus': 1+n, 'cv': 15, 'hv': 15}
    bldg_ctx_dict = {}
    for i in range(bldg_config['ahus']):
        if i<n:
            continue
        template_name = 'multiple-zone-ahu'
        ahu_name = f'ahu_{i}'
        ahu = ctx[template_name](name=ahu_name)
        ahu.bindings = {k: BLDG[f"{template_name}_{k}_{i}"] for k in ahu.parameters}
        assemble_ahu(ahu.bindings)
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
            ctx['feeds'](name = ahu['name'], outlet_cp = ahu_name + 'out', connection = ahu_name + 'con', inlet_cp = cvav.bindings['air-inlet-connectionpoint'], target = cvav['name'])
            for k,v in cvav.bindings.items():
                # g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDF[f"_{cv+1}"], v))
                g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDFS[f"member"], v))
            # print(cvav.bindings)
        for hv in range(bldg_config['hv']):
            template_name = 'vav-with-reheat'
            hv_name = f'hvav_{i}_{hv}'
            hvav = ctx[template_name](name=hv_name)
            hvav.bindings = {k: BLDG[f"{template_name}_{k}_{i}_{hv}"] for k in hvav.parameters}
            ctx['feeds'](name = ahu['name'], outlet_cp = ahu_name + 'out', connection = ahu_name + 'con', inlet_cp = hvav.bindings['name-air-inlet-connectionpoint'], target = hvav['name'])
            for k,v in hvav.bindings.items():
                # g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDF[f"_{hv+1}"], v))
                g.add((BLDG[f"{template_name}-{k.replace('name-','')}"], RDFS[f"member"], v))

    if n < 1:
        wrapper_dict = get_wrapper_dict(ctx)
        template_types = wrapper_dict.keys()

    if n < 1:
        skip_templates = ['feeds']
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
            connection_template = brick_tmpl.get_template_by_name('feeds')
            g = g+ connection_template.inline_dependencies().evaluate({
                'inlet_cp': BLDG['vav-cooling-only-name']+'_in', 
                'connection': BLDG['multiple-zone-ahu-name']+'_cn', 
                'name': BLDG['multiple-zone-ahu-name'],
                'target': BLDG['vav-cooling-only-name'],
                'outlet_cp': BLDG['multiple-zone-ahu-name']+'_out',
            })
            g = g+ connection_template.inline_dependencies().evaluate({
                'inlet_cp': BLDG['vav-with-reheat-name']+'_in', 
                'connection': BLDG['multiple-zone-ahu-name']+'_cn', 
                'name': BLDG['multiple-zone-ahu-name'],
                'target': BLDG['vav-with-reheat-name'],
                'outlet_cp': BLDG['multiple-zone-ahu-name']+'_out',
            })


    # %%
    # add inverse cnx
    def add_inverse_cnx(g):
        query = """ CONSTRUCT {
            ?s s223:cnx ?o
        }
        WHERE {
            ?o s223:cnx ?s
        }
        """
        g += g.query(query).graph

    # %%
    add_inverse_cnx(g)

    # %%
    g_no_data = g.query("""
                CONSTRUCT {
                    ?s ?p ?o .
                }
                WHERE {
                ?s ?p ?o .
                FILTER (?p != rdfs:member) .
                }
                    """).graph

    def get_label(s):
        name= str(s).rsplit('-')[-1] if str(s).rsplit('-')[-1] != 'name' else str(s).rsplit('-')[-2]
        return Literal(name)
    for s,p,o in g_no_data.triples((None,None,None)):    
        if p == A:
            continue               
        if p == BRICK.hasPoint:
            g_no_data.add((o, A, BRICK.Point))
        g_no_data.add((s, RDFS.label, get_label(s)))
        g_no_data.add((o, RDFS.label, get_label(o)))

    g_no_data.bind('bldg',BLDG)

    # %%
    bldg.add_graph(ctx.compile())
    add_inverse_cnx(bldg.graph)

    # %% [markdown]
    # # Querying

    # %%
    # example query. What is the discharge air temperature of cooling only VAVs
    import sys
    import os
    # current_dir = os.path.dirname(__file__)
    # utils_path = os.path.abspath(os.path.join(current_dir, '..', 'utils'))
    sys.path.insert(0, '../../utils')
    from utils import query_to_df, get_prefixes
    model_length.append(len(bldg.graph))
    # %%
    bldg_graph = Graph(store = 'Oxigraph')
    for s,p,o in bldg.graph.triples((None,None,None)):
        bldg_graph.add((s,p,o))
    for s,p,o in g.triples((None,None,None)):
        bldg_graph.add((s,p,o))
    # %%
    print('beginning querying')
    st = time()
    bldg_query = get_prefixes(bldg.graph)
    bldg_query += """
    SELECT ?dat ?vav ?ahu
    WHERE {
        ?dat a s223:QuantifiableObservableProperty .
        ?vav a s223:SingleDuctTerminal ;
            s223:contains ?dmp .
        ?dmp a s223:Damper . 
        ?vav s223:cnx ?outlet_cp . 
        ?outlet_cp a s223:OutletConnectionPoint ;
            s223:hasProperty ?dat .
        ?ahu a s223:AirHandlingUnit ;
            s223:cnx* ?vav .
        FILTER NOT EXISTS {
            ?vav s223:contains ?rc .
            ?rc a s223:Coil .
        }
    }
    """
    query_to_df(bldg_query, bldg_graph)
    et = time()
    elapsed_time = et - st
    not_condensed_t.append(time() - st)

    st = time()
    bldg_query = get_prefixes(bldg.graph)
    bldg_query += """
    SELECT ?dat ?vav ?ahu
    WHERE {
        ?dat a s223:QuantifiableObservableProperty .
        ?vavC a s223:SingleDuctTerminal, rdf:Seq ;
            rdfs:member ?vav ;
            s223:contains ?dmp .
        ?dmp a s223:Damper . 
        ?vav s223:cnx ?outlet_cp . 
        ?outlet_cp a s223:OutletConnectionPoint ;
            s223:hasProperty ?dat .
        ?ahu a s223:AirHandlingUnit ;
            s223:cnx* ?vav .
        FILTER NOT EXISTS {
            ?vavC s223:contains ?rc .
            ?rc a s223:Coil .
        }
    }
    """
    query_to_df(bldg_query, bldg_graph)
    condensed_t.append(time() - st)


    # import pyshacl 
    # ont = Graph()
    # print("parsing ontology")
    # ont.parse('../ontologies/223p.ttl')
    # print("copying graph")
    # for s,p,o in bldg_graph.triples((None,None,None)):
    #     ont.add((s,p,o))
    # st = time()
    # print('validating')
    # pyshacl.validate(ont, ont)
    # et = time()
    # not_condensed_reasoning_t.append(et-st)

    # ont = g.parse('../ontologies/223p.ttl')
    # for s,p,o in g.triples((None,None,None)):
    #     ont.add((s,p,o))
    # st = time()
    # pyshacl.validate(ont, ont)
    # et = time()
    # condensed_reasoning_t.append(et-st)

import pandas as pd 
df = pd.DataFrame({
    'model_length': model_length,
    'not_condensed_t': not_condensed_t,
    'condensed_t': condensed_t,
    # 'not_condensed_reasoning_t': not_condensed_reasoning_t,
    # 'condensed_reasoning_t': condensed_reasoning_t,
})
df.to_csv('query-time-s223.csv')
import matplotlib.pyplot as plt
plt.ylabel('Query Time (seconds)')
plt.plot([f"{n/1000}k" for n in model_length],not_condensed_t, label='Without Condensed Representation')
plt.plot([f"{n/1000}k" for n in model_length],condensed_t, label='With Condensed Representation')
plt.xlabel('Size of Model (1000s of triples)')
# plt.xticks(model_length, [f'{1+i} [{x}]' for i,x in enumerate(model_length)])
plt.legend()
plt.savefig('query-time-s223.png')