# google.adk.tools.google_maps_grounding_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google-adk-tools-google-maps-grounding-tool-module)

---

google.adk.tools.google_maps_grounding_tool module


class google.adk.tools.google_maps_grounding_tool.GoogleMapsGroundingTool
Bases: BaseTool
A built-in tool that is automatically invoked by Gemini 2 models to ground query results with Google Maps.
This tool operates internally within the model and does not require or perform
local code execution.
Only available for use with the VertexAI Gemini API (e.g.
GOOGLE_GENAI_USE_VERTEXAI=TRUE)


async process_llm_request(*, tool_context, llm_request)
Processes the outgoing LLM request for this tool.
Use cases:
- Most common use case is adding this tool to the LLM request.
- Some tools may just preprocess the LLM request before it's sent out.

Return type:
None

Parameters:

tool_context – The context of the tool.
llm_request – The outgoing LLM request, mutable this method.
