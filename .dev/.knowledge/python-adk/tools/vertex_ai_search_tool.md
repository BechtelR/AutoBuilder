# google.adk.tools.vertex_ai_search_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.vertex_ai_search_tool)

---


google.adk.tools.vertex_ai_search_tool module


class google.adk.tools.vertex_ai_search_tool.VertexAiSearchTool(*, data_store_id=None, data_store_specs=None, search_engine_id=None, filter=None, max_results=None, bypass_multi_tools_limit=False)
Bases: BaseTool
A built-in tool using Vertex AI Search.


data_store_id
The Vertex AI search data store resource ID.




search_engine_id
The Vertex AI search engine resource ID.


To dynamically customize the search configuration at runtime (e.g., set
filter based on user context), subclass this tool and override the
_build_vertex_ai_search_config method.
Example
```python
class DynamicFilterSearchTool(VertexAiSearchTool):


def _build_vertex_ai_search_config(self, ctx: ReadonlyContext

) -> types.VertexAISearch:user_id = ctx.state.get(‘user_id’)
return types.VertexAISearch(

datastore=self.data_store_id,
engine=self.search_engine_id,
filter=f”user_id = ‘{user_id}’”,
max_results=self.max_results,

)



```
Initializes the Vertex AI Search tool.

Parameters:

data_store_id – The Vertex AI search data store resource ID in the format
of
“projects/{project}/locations/{location}/collections/{collection}/dataStores/{dataStore}”.
data_store_specs – Specifications that define the specific DataStores to be
searched. It should only be set if engine is used.
search_engine_id – The Vertex AI search engine resource ID in the format of
“projects/{project}/locations/{location}/collections/{collection}/engines/{engine}”.
filter – The filter to apply to the search results.
max_results – The maximum number of results to return.
bypass_multi_tools_limit – Whether to bypass the multi tools limitation,
so that the tool can be used with other tools in the same agent.


Raises:

ValueError – If both data_store_id and search_engine_id are not specified
