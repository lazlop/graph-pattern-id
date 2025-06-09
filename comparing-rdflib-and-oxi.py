#%%
from rdflib import Graph

g = Graph(store = 'Oxigraph')
g.parse("reasoned_build.ttl", format="turtle")

query = """
        SELECT * WHERE 
        { ?s a s223:AirHandlingUnit ; 
            s223:cnx* ?uft . 
        ?uft a s223:FanPoweredTerminal ;
          s223:cnx* ?d . 
        ?d a s223:DomainSpace . 
        FILTER NOT EXISTS { ?d s223:cnx ?outdoors. 
            ?outdoors a s223:OutdoorSpace . }
        } """

# result = g.query(f"SELECT * WHERE {{ ?s ?p ?o . }}")
result = g.query(query)
print(len(result))
# %%
# on SDH model 