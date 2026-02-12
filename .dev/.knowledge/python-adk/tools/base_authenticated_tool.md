# google.adk.tools.base_authenticated_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.base_authenticated_tool)

---


google.adk.tools.base_authenticated_tool module


class google.adk.tools.base_authenticated_tool.BaseAuthenticatedTool(*, name, description, auth_config=None, response_for_auth_required=None)
Bases: BaseTool
A base tool class that handles authentication before the actual tool logic
gets called. Functions can accept a special credential argument which is the
credential ready for use.(Experimental)

Parameters:

name – The name of the tool.
description – The description of the tool.
auth_config – The auth configuration of the tool.
response_for_auth_required – The response to return when the tool is
requesting auth credential from the client. There could be two case,
the tool doesn’t configure any credentials
(auth_config.raw_auth_credential is missing) or the credentials
configured is not enough to authenticate the tool (e.g. an OAuth
client id and client secret are configured) and needs client input
(e.g. client need to involve the end user in an oauth flow and get
back the oauth response.)





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







