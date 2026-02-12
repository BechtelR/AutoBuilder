# google.adk.tools.load_artifacts_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.load_artifacts_tool)

---


google.adk.tools.load_artifacts_tool module


class google.adk.tools.load_artifacts_tool.LoadArtifactsTool
Bases: BaseTool
A tool that loads the artifacts and adds them to the session.


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







async run_async(*, args, tool_context)
Runs the tool with the given arguments and context.

Return type:
Any



Note

Required if this tool needs to run at the client side.
Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for
Gemini.



Parameters:

args – The LLM-filled arguments.
tool_context – The context of the tool.


Returns:
The result of running the tool.







