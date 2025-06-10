
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
