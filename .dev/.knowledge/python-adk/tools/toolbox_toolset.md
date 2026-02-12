# google.adk.tools.toolbox_toolset

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.toolbox_toolset)

---


google.adk.tools.toolbox_toolset module


class google.adk.tools.toolbox_toolset.ToolboxToolset(server_url, toolset_name=None, tool_names=None, auth_token_getters=None, bound_params=None, credentials=None, additional_headers=None, **kwargs)
Bases: BaseToolset
A class that provides access to toolbox toolsets.
Example:
`python
toolbox_toolset = ToolboxToolset("http://127.0.0.1:5000")
`
Initializes the ToolboxToolset.

Parameters:

server_url – The URL of the toolbox server.
toolset_name – (Optional) The name of the toolbox toolset to load.
tool_names – (Optional) The names of the tools to load.
auth_token_getters – (Optional) A mapping of authentication service names
to callables that return the corresponding authentication token. see:
https://github.com/googleapis/mcp-toolbox-sdk-python/tree/main/packages/toolbox-core#authenticating-tools

for details.


bound_params – (Optional) A mapping of parameter names to bind to specific
values or callables that are called to produce values as needed. see:
https://github.com/googleapis/mcp-toolbox-sdk-python/tree/main/packages/toolbox-core#binding-parameter-values

for details.


credentials – (Optional) toolbox_adk.CredentialConfig object.
additional_headers – (Optional) Static headers mapping.
**kwargs – Additional arguments passed to the underlying
toolbox_adk.ToolboxToolset.



The resulting ToolboxToolset will contain both tools loaded by tool_names
and toolset_name.
Note: toolset_name and tool_names are optional.
If both are omitted, all tools are loaded.


async close()
Performs cleanup and releases resources held by the toolset.

Note
This method is invoked, for example, at the end of an agent server’s
lifecycle or when the toolset is no longer needed. Implementations
should ensure that any open connections, files, or other managed
resources are properly released to prevent leaks.





async get_tools(readonly_context=None)
Return all tools in the toolset based on the provided context.

Return type:
list[BaseTool]

Parameters:
readonly_context (ReadonlyContext, optional) – Context used to filter tools
available to the agent. If None, all tools in the toolset are returned.

Returns:
A list of tools available under the specified context.

Return type:
list[BaseTool]







