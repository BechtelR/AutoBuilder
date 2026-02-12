# google.adk.tools.base_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.base_tool)

---


google.adk.tools.base_tool module


class google.adk.tools.base_tool.BaseTool(*, name, description, is_long_running=False, custom_metadata=None)
Bases: ABC
The base class for all tools.


custom_metadata: dict[str, Any] | None = None
The custom metadata of the BaseTool.
An optional key-value pair for storing and retrieving tool-specific metadata,
such as tool manifests, etc.
NOTE: the entire dict must be JSON serializable.




description: str
The description of the tool.




classmethod from_config(config, config_abs_path)
Creates a tool instance from a config.
This default implementation uses inspect to automatically map config values
to constructor arguments based on their type hints. Subclasses should
override this method for custom initialization logic.

Return type:
TypeVar(SelfTool, bound= BaseTool)

Parameters:

config – The config for the tool.
config_abs_path – The absolute path to the config file that contains the
tool config.


Returns:
The tool instance.






is_long_running: bool = False
Whether the tool is a long running operation, which typically returns a
resource id first and finishes the operation later.




name: str
The name of the tool.




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







