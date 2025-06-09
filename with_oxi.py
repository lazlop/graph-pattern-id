#%% 
from pyoxigraph import * 
from namespaces import *
from rdflib import Graph

# for oxygraph need s223 to end with a '/' for the namespace check, or not 
# S223 = Namespace("http://data.ashrae.org/standard223/")
store = Store()
dg = NamedNode("urn:data-graph")
sg = NamedNode("urn:schema-graph")
# store.load(path = "vrf-model-cut.ttl", format = RdfFormat.TURTLE, to_graph=dg)
store.load(path = "vrf-model.ttl", format = RdfFormat.TURTLE, to_graph=dg)
EX = Namespace("http://data.ashrae.org/standard223/data/scb-vrf#")
store.load(path = "223p.ttl", format = RdfFormat.TURTLE, to_graph=sg)

g = Graph()
g.parse("223p.ttl", format="turtle")
prefixes = get_prefixes(g)
# %%
# list(store.query("""
#     SELECT ?s ?p ?o WHERE {
#         ?s ?p ?o .
#     }
#     """))
# %%
# g = parse("vrf-model-cut.ttl", format=RdfFormat.TURTLE)
# %%

# Inserting the string to filer by didn't work, had to use namespace
def get_class(node, ns = S223):
    
    query = f"""
    {prefixes}
    # PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class WHERE {{
        {str(node)} a ?class . 
        FILTER NOT EXISTS {{
            {str(node)} a ?subclass .
            ?subclass rdfs:subClassOf ?class .
        }}
        FILTER(STRSTARTS(STR(?class), str(s223:)))
    }} """
    r = store.query(query, use_default_graph_as_union=True)
    return r

def get_local_name(node):
    node = str(node).replace('<', '').replace('>', '')
    if '#' in node:
        return node.rpartition('#')[-1]
    else:
        return node.rpartition('/')[-1]
    
def check_ns(node, ns = EX):
    # would have been better to do with sparql
    # have to get rid of starting bracket
    if '#' in str(node):
        node_ns = str(node).rpartition('#')[0][1:]
    else:
        node_ns = str(node).rpartition('/')[0][1:]
    
    ns_without_delimiter = str(ns)[:-1]
    return ns_without_delimiter == node_ns

def get_groups():
    cg = NamedNode("urn:class-graph")
    class_triples = set()
    subject_list = []
    object_list = []
    for quad in store.quads_for_pattern(None,None,None, dg):
        if not check_ns(quad.subject):
            # print("subject not in namespace")
            continue
        if not check_ns(quad.object):
            # print("object not in namespace")
            continue
        if not check_ns(quad.predicate, ns = S223):
            # print("object not in namespace")
            continue
        subjects = list(get_class(quad.subject))
        objects = list(get_class(quad.object))
        if len(subjects) == 0:
            labels = list(store.quads_for_pattern(quad.subject,NamedNode(RDFS.label),None,dg))
            if len(labels) > 0:
                label = labels[0].object.value
                subject_list.append(label)
            else:
                subject_list.append("none")
            continue
        else:
            subject_class = subjects[0]['class'].value
            subject_list.append(subject_class)
        if len(objects) == 0:
            labels = list(store.quads_for_pattern(quad.object,NamedNode(RDFS.label),None,dg))
            if len(labels) > 0:
                label = labels[0].object.value
                object_list.append(label)
            # else:
                # All results for this were other classes defined in bob, will do nothing for now
                # object_list.append(quad.object)
            continue 
        else:
            object_class = objects[0]['class'].value
            object_list.append(object_class)
            
        class_triples.add((get_local_name(subject_class), get_local_name(quad.predicate), get_local_name(object_class)))
    return subject_list, object_list, class_triples

if __name__ == "__main__":
    s,o,t  = get_groups()
    # display(set(s))
    # display(set(o))
    display(t)
# %%
