# google.adk.tools.enterprise_search_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.enterprise_search_tool)

---


google.adk.tools.enterprise_search_tool module


class google.adk.tools.enterprise_search_tool.EnterpriseWebSearchTool
Bases: BaseTool
A Gemini 2+ built-in tool using web grounding for Enterprise compliance.
NOTE: This tool is not the same as Vertex AI Search, which is used to be
called “Enterprise Search”.
See the documentation for more details:
https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/web-grounding-enterprise.
Initializes the Enterprise Web Search tool.


async process_llm_request(*, tool_context, llm_request)
Processes the outgoing LLM request for this tool.
Use cases:
- Most common use case is adding this tool to the LLM request.
- Some tools may just preprocess the LLM request before it’s sent out.

Return type:
None

Parameters:

tool_context – The context of the tool.
llm_request – The outgoing LLM request, mutable this method.








