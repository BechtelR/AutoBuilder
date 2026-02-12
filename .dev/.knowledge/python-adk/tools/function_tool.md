# google.adk.tools.function_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.function_tool)

---


google.adk.tools.function_tool module


class google.adk.tools.function_tool.FunctionTool(func, *, require_confirmation=False)
Bases: BaseTool
A tool that wraps a user-defined Python function.


func
The function to wrap.


Initializes the FunctionTool. Extracts metadata from a callable object.

Parameters:

func – The function to wrap.
require_confirmation – Whether this tool requires confirmation. A boolean or
a callable that takes the function’s arguments and returns a boolean. If
the callable returns True, the tool will require confirmation from the
user.





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







