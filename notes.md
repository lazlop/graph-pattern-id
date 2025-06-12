
start with a node. 
Depth first search
Query the graph, if the amount of totally unique results is greater than 1, continue
walk and add to the query. If one column has only 1 value, split it into another group. 
continue to walk the graph, storing each previous query until the amount of results drops to 1 or less 
The step before is a group. 

Remove from the graph everything included in the group

start at a new point and repeat

Do this until the graph is empty

Keep track of the connects each group has to the nodes in other groups. 

Lets say we have a bunch of vavs that either connect to 1 space or two spaces. Are these meaningfully differernt? 
would I want to distinguish between the 1 space results and the two space results. I'd need a separate sparql structure to do this.
Thinking about it as whether or not something contains 1 or two fans, clearly these should be distinguished. 
This can be done by determining overlap of rows. Each row (result) must be fully independent. if rows are not fully independent, keep adding to the query

Graph would have ones with two fans, that would get added to the query with contains fan 2 and filter fan1 != fan2. Then the rows would be independent. 
    
triples in query data ARE namespaced
query data is each triple to query for as class relation class. The second time a class appears it'll have an ascending number


The SPARQL query created by looking at the relationships and classes seems to work on the test graphs to identify the patterns I want 

In completing this I did many things that I did not need to do, had I understood better what the sparql results would be instead of taking an incorrect guess. I didn't need to:
 - do the graph depth first search
 - create the query at each step or based on an arbitrary collection of triples - could have just done it based on the graph 
 - already have some graph to sparql stuff ready to go 
 - try to create signatures and paths to group nodes one by one. (if the SPARQL plan works)
 - if my solution is essentially just a SPARQL query, is this even worth creating a short paper of in buildsys? 

Maybe the dfs is good because the SPARQL process only properly creates groups for things that are connected.
However, may make more sense to just render the groups again and reconcile. 

Remaking the groups into a graph and then running the process again does generate the groups I want and expect. 

TODO: 
Maybe separate and tackle by type to make SPARQL queries smaller? 
Just the thing and everything directly related to it to create the initial groups, then se see how groups relate to each other? 
    This definitley won't have the potentially useful intermediate steps of the process with the subgroups before hte larger groups
    Can do like: 
        1) Get all VAVs - ask if they are the same. Create groups for which are the same 
        2) Get all AHUs - asl of they are the same. Create groups for which they are the same 
        3) Compare how each VAV connects to each AHU, create final groups for different kinds of connection. 
        Relies on knowing what is included in a VAV and what is included in an AHU - but maybe these aren't terrible assumptions. 
    
Probably want to do the writeup and see if this idea has merrit before doing any optimization. 

Can do separate queries to create groups for each type of thing then coalesce? 
maybe something a little closer to constructing groups while walking the graph?
