# google.adk.tools.preload_memory_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.preload_memory_tool)

---


google.adk.tools.preload_memory_tool module


class google.adk.tools.preload_memory_tool.PreloadMemoryTool
Bases: BaseTool
A tool that preloads the memory for the current user.
This tool will be automatically executed for each llm_request, and it won’t be
called by the model.
NOTE: Currently this tool only uses text part from the memory.


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








