# Graph Pattern Identification for RDF Models of Buildings, testing the B-Schema

Repository for testing the concise, ontology-agnostic representation of semantic models of buildings. Intended to enable ease of use for visualization, querying, SHACL validation-driven workflows, and using LLMs.


![image](https://github.com/user-attachments/assets/425127fe-6492-4a81-b676-dfbcfd006338)


Make sure you have [uv](https://docs.astral.sh/uv/) installed. 

Clone the repo, and use the package to run via python, or run via CLI using 

```
uv pip install "git+https://github.com/lazlop/graph-pattern-id.git"
uv run create-bschema
```

You can even run the code without installing using 

`uvx --from 'bschema @ git+https://github.com/lazlop/graph-pattern-id.git' create-bschema`