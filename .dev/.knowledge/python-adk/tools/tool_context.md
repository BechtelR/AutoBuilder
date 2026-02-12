# google.adk.tools.tool_context

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.tool_context)

---


google.adk.tools.tool_context module


class google.adk.tools.tool_context.ToolContext(invocation_context, *, function_call_id=None, event_actions=None, tool_confirmation=None)
Bases: CallbackContext
The context of the tool.
This class provides the context for a tool invocation, including access to
the invocation context, function call ID, event actions, and authentication
response. It also provides methods for requesting credentials, retrieving
authentication responses, listing artifacts, and searching memory.


invocation_context
The invocation context of the tool.




function_call_id
The function call id of the current tool call. This id was
returned in the function call event from LLM to identify a function call.
If LLM didn’t return this id, ADK will assign one to it. This id is used
to map function call response to the original function call.




event_actions
The event actions of the current tool call.




tool_confirmation
The tool confirmation of the current tool call.




property actions: EventActions




get_auth_response(auth_config)
Gets the auth response credential from session state.
This method retrieves an authentication credential that was previously
stored in session state after a user completed an OAuth flow or other
authentication process.

Return type:
AuthCredential

Parameters:
auth_config – The authentication configuration for the credential.

Returns:
The auth credential from the auth response, or None if not found.






request_confirmation(*, hint=None, payload=None)
Requests confirmation for the given function call.

Return type:
None

Parameters:

hint – A hint to the user on how to confirm the tool call.
payload – The payload used to confirm the tool call.







request_credential(auth_config)

Return type:
None






async search_memory(query)
Searches the memory of the current user.

Return type:
SearchMemoryResponse







