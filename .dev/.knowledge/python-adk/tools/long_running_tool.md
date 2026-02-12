# google.adk.tools.long_running_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.long_running_tool)

---


google.adk.tools.long_running_tool module


class google.adk.tools.long_running_tool.LongRunningFunctionTool(func)
Bases: FunctionTool
A function tool that returns the result asynchronously.
This tool is used for long-running operations that may take a significant
amount of time to complete. The framework will call the function. Once the
function returns, the response will be returned asynchronously to the
framework which is identified by the function_call_id.
Example:
`python
tool = LongRunningFunctionTool(a_long_running_function)
`


is_long_running
Whether the tool is a long running operation.


Initializes the FunctionTool. Extracts metadata from a callable object.

Parameters:

func – The function to wrap.
require_confirmation – Whether this tool requires confirmation. A boolean or
a callable that takes the function’s arguments and returns a boolean. If
the callable returns True, the tool will require confirmation from the
user.






