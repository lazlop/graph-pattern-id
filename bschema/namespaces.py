# %%
from rdflib.namespace import (
    XSD,
    RDFS,
    SH,
    Namespace,
    RDF,
)

BS = Namespace("urn:bschema#")

EX = Namespace("urn:example#")

HPF = Namespace(f"urn:hpflex#")
HPFS = Namespace("urn:hpflex/shapes#")

PARAM = Namespace("urn:___param___#")
# all versions of Brick > 1.1 have these namespaces
BRICK = Namespace("https://brickschema.org/schema/Brick#")
TAG = Namespace("https://brickschema.org/schema/BrickTag#")
BSH = Namespace("https://brickschema.org/schema/BrickShape#")
REF = Namespace("https://brickschema.org/schema/Brick/ref#")
REC = Namespace("https://w3id.org/rec#")

S4BLDG = Namespace("https://saref.etsi.org/saref4bldg#")
S4ENER = Namespace("https://saref.etsi.org/saref4ener#")
SAREF = Namespace("https://saref.etsi.org/core#")

# defaults
OWL = Namespace("http://www.w3.org/2002/07/owl#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SH = Namespace("http://www.w3.org/ns/shacl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
BOB = Namespace("http://data.ashrae.org/standard223/si-builder#")
# QUDT namespaces
QUDT = Namespace("http://qudt.org/schema/qudt/")
QK = Namespace("http://qudt.org/vocab/quantitykind/")
DV = Namespace("http://qudt.org/vocab/dimensionvector/")
UNIT = Namespace("http://qudt.org/vocab/unit/")

# ASHRAE namespaces
BACNET = Namespace("http://data.ashrae.org/bacnet/2020#")
S223 = Namespace("http://data.ashrae.org/standard223#")

BM = Namespace("https://nrel.gov/BuildingMOTIF#")
CONSTRAINT = Namespace("https://nrel.gov/BuildingMOTIF/constraints#")
S223 = Namespace("http://data.ashrae.org/standard223#")

A = RDF.type

BNODE_BASE = "https://rdflib.github.io/.well-known/genid/rdflib/"

def bind_prefixes(graph):
    """Associate common prefixes with the graph.

    :param graph: graph
    :type graph: rdflib.Graph
    """
    graph.bind("xsd", XSD)
    graph.bind("rdf", RDF)
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("skos", SKOS)
    graph.bind("sh", SH)
    graph.bind("quantitykind", QK)
    graph.bind("qudt", QUDT)
    graph.bind("unit", UNIT)
    graph.bind("ref", REF)
    graph.bind("rec", REC)
    graph.bind("brick", BRICK)
    graph.bind("tag", TAG)
    graph.bind("bsh", BSH)
    graph.bind("P", PARAM)
    graph.bind("constraint", CONSTRAINT)
    graph.bind("bmotif", BM)
    graph.bind("hpflex", HPF)
    graph.bind("hpfs", HPFS)
    graph.bind("s223", S223)
    graph.bind("ex", EX)
    graph.bind("bs", BS)
    graph.bind("bob", BOB)
    graph.bind("bacnet", BACNET)
    graph.bind("s4bldg", S4BLDG)
    graph.bind("s4ener", S4ENER)
    graph.bind("saref", SAREF)

namespace_dict = {
    "xsd": XSD,
    "rdf": RDF,
    "owl": OWL,
    "rdfs": RDFS,
    "skos": SKOS,
    "sh": SH,
    "quantitykind": QK,
    "qudt": QUDT,
    "unit": UNIT,
    "brick": BRICK,
    "ref": REF,
    "tag": TAG,
    "bsh": BSH,
    "P": PARAM,
    "constraint": CONSTRAINT,
    "bmotif": BM,
    "hpflex": HPF,
    "hpfs": HPFS,
    "s223": S223,
    "ex1": "http://data.ashrae.org/standard223/data/scb-vrf#",
    "ex":EX,
    "bs":BS,
    "bob":BOB,
    "s4bldg":S4BLDG,
    "s4ener":S4ENER,
    "saref":SAREF
}

prefix_dict = {value: key for key, value in namespace_dict.items()}

def get_prefixes(g):
    return "\n".join(
        f"PREFIX {prefix}: <{namespace}>"
        for prefix, namespace in g.namespace_manager.namespaces()
    )


def convert_to_prefixed(uri, g):
    try:
        prefix, uri_ref, local_name = g.compute_qname(uri)
        return f"{prefix}:{local_name}"
    except Exception as e:
        print(e)
        return uri
