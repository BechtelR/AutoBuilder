# google.adk.tools.url_context_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.url_context_tool)

---


google.adk.tools.url_context_tool module


class google.adk.tools.url_context_tool.UrlContextTool
Bases: BaseTool
A built-in tool that is automatically invoked by Gemini 2 models to retrieve content from the URLs and use that content to inform and shape its response.
This tool operates internally within the model and does not require or perform
local code execution.


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








