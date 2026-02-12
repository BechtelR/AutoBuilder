# google.adk.tools.base_toolset

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.base_toolset)

---


google.adk.tools.base_toolset module


class google.adk.tools.base_toolset.BaseToolset(*, tool_filter=None, tool_name_prefix=None)
Bases: ABC
Base class for toolset.
A toolset is a collection of tools that can be used by an agent.
Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.





async close()
Performs cleanup and releases resources held by the toolset.

Return type:
None



Note
This method is invoked, for example, at the end of an agent server’s
lifecycle or when the toolset is no longer needed. Implementations
should ensure that any open connections, files, or other managed
resources are properly released to prevent leaks.





classmethod from_config(config, config_abs_path)
Creates a toolset instance from a config.

Return type:
TypeVar(SelfToolset, bound= BaseToolset)

Parameters:

config – The config for the tool.
config_abs_path – The absolute path to the config file that contains the
tool config.


Returns:
The toolset instance.






get_auth_config()
Returns the auth config for this toolset. ADK will make sure the
‘exchanged_auth_credential’ field in the config is populated with
ready-to-use credential (e.g. oauth token for OAuth flow) before calling
get_tools method or execute any tools returned by this toolset. Thus toolset
can use this credential either for tool listing or tool calling. If tool
calling needs a different credential from ADK client, call
tool_context.request_credential in the tool.
Toolsets that support authentication should override this method to return
an AuthConfig constructed from their auth_scheme, auth_credential, and
optional credential_key parameters.

Return type:
Optional[AuthConfig]

Returns:
AuthConfig if the toolset has authentication configured, None otherwise.






abstractmethod async get_tools(readonly_context=None)
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






final async get_tools_with_prefix(readonly_context=None)
Return all tools with optional prefix applied to tool names.
This method calls get_tools() and applies prefixing if tool_name_prefix is provided.

Return type:
list[BaseTool]

Parameters:
readonly_context (ReadonlyContext, optional) – Context used to filter tools
available to the agent. If None, all tools in the toolset are returned.

Returns:
A list of tools with prefixed names if tool_name_prefix is provided.

Return type:
list[BaseTool]






async process_llm_request(*, tool_context, llm_request)
Processes the outgoing LLM request for this toolset. This method will be
called before each tool processes the llm request.

Return type:
None


Use cases:
- Instead of let each tool process the llm request, we can let the toolset

process the llm request. e.g. ComputerUseToolset can add computer use
tool to the llm request.


Parameters:

tool_context – The context of the tool.
llm_request – The outgoing LLM request, mutable this method.









class google.adk.tools.base_toolset.ToolPredicate(*args, **kwargs)
Bases: Protocol
Base class for a predicate that defines the interface to decide whether a
tool should be exposed to LLM. Toolset implementer could consider whether to
accept such instance in the toolset’s constructor and apply the predicate in
get_tools method.



