# google.adk.tools package¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools

***class*google.adk.tools.APIHubToolset(***,*apihub_resource_name*,*access_token**=**None*,*service_account_json**=**None*,*name**=**''*,*description**=**''*,*lazy_load_spec**=**False*,*auth_scheme**=**None*,*auth_credential**=**None*,*apihub_client**=**None*,*tool_filter**=**None*)¶**
Bases:[BaseToolset

APIHubTool generates tools from a given API Hub resource.

Examples:


```
apihub_toolset = APIHubToolset(
    apihub_resource_name="projects/test-project/locations/us-central1/apis/test-api",
    service_account_json="...",
    tool_filter=lambda tool, ctx=None: tool.name in ('my_tool',
    'my_other_tool')
)

# Get all available tools
agent = LlmAgent(tools=apihub_toolset)
```

**apihub_resource_name**is the resource name from API Hub. It must include API name, and can optionally include API version and spec name.

If apihub_resource_name includes a spec resource name, the content of that spec will be used for generating the tools.

If apihub_resource_name includes only an api or a version name, the first spec of the first version of that API will be used.

Initializes the APIHubTool with the given parameters.

Examples:


```
apihub_toolset = APIHubToolset(
    apihub_resource_name="projects/test-project/locations/us-central1/apis/test-api",
    service_account_json="...",
)

# Get all available tools
agent = LlmAgent(tools=[apihub_toolset])

apihub_toolset = APIHubToolset(
    apihub_resource_name="projects/test-project/locations/us-central1/apis/test-api",
    service_account_json="...",
    tool_filter = ['my_tool']
)
# Get a specific tool
agent = LlmAgent(tools=[
    ...,
    apihub_toolset,
])
```

**apihub_resource_name**is the resource name from API Hub. It must include API name, and can optionally include API version and spec name.

If apihub_resource_name includes a spec resource name, the content of that spec will be used for generating the tools.

If apihub_resource_name includes only an api or a version name, the first spec of the first version of that API will be used.

Example:

projects/xxx/locations/us-central1/apis/apiname/…

[https://console.cloud.google.com/apigee/api-hub/apis/apiname?project=xxx


**Parameters:**
**apihub_resource_name**– The resource name of the API in API Hub. Example:projects/test-project/locations/us-central1/apis/test-api.

**access_token**– Google Access token. Generate with gcloud cligcloud auth print-access-token. Used for fetching API Specs from API Hub.

**service_account_json**– The service account config as a json string. Required if not using default service credential. It is used for creating the API Hub client and fetching the API Specs from API Hub.

**apihub_client**– Optional custom API Hub client.

**name**– Name of the toolset. Optional.

**description**– Description of the toolset. Optional.

**auth_scheme**– Auth scheme that applies to all the tool in the toolset.

**auth_credential**– Auth credential that applies to all the tool in the toolset.

**lazy_load_spec**– If True, the spec will be loaded lazily when needed. Otherwise, the spec will be loaded immediately and the tools will be generated during initialization.

**tool_filter**– The filter used to filter the tools in the toolset. It can be either a tool predicate or a list of tool names of the tools to expose.


***async*close()¶**
Performs cleanup and releases resources held by the toolset.

Note

This method is invoked, for example, at the end of an agent server’s lifecycle or when the toolset is no longer needed. Implementations should ensure that any open connections, files, or other managed resources are properly released to prevent leaks.


**get_auth_config()¶**
Returns the auth config for this toolset.

ADK will populate exchanged_auth_credential on this config before calling get_tools(). The toolset can then access the ready-to-use credential via self._auth_config.exchanged_auth_credential.


**Return type:**
Optional[AuthConfig]


***async*get_tools(*readonly_context**=**None*)¶**
Retrieves all available tools.


**Return type:**
List[[RestApiTool]


**Returns:**
A list of all available RestApiTool objects.


***class*google.adk.tools.AgentTool(*agent*,*skip_summarization**=**False*,***,*include_plugins**=**True*)¶**
Bases:[BaseTool

A tool that wraps an agent.

This tool allows an agent to be called as a tool within a larger application. The agent’s input schema is used to define the tool’s input parameters, and the agent’s output is returned as the tool’s result.


**agent¶**
The agent to wrap.


**skip_summarization¶**
Whether to skip summarization of the agent output.


**include_plugins¶**
Whether to propagate plugins from the parent runner context to the agent’s runner. When True (default), the agent will inherit all plugins from its parent. Set to False to run the agent with an isolated plugin environment.


***classmethod*from_config(*config*,*config_abs_path*)¶**
Creates a tool instance from a config.

This default implementation uses inspect to automatically map config values to constructor arguments based on their type hints. Subclasses should override this method for custom initialization logic.


**Return type:**
[AgentTool


**Parameters:**
**config**– The config for the tool.

**config_abs_path**– The absolute path to the config file that contains the tool config.


**Returns:**
The tool instance.


**populate_name()¶**

**Return type:**
Any


***async*run_async(***,*args*,*tool_context*)¶**
Runs the tool with the given arguments and context.


**Return type:**
Any

Note

Required if this tool needs to run at the client side.

Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.


**Parameters:**
**args**– The LLM-filled arguments.

**tool_context**– The context of the tool.


**Returns:**
The result of running the tool.


***class*google.adk.tools.ApiRegistry(*api_registry_project_id*,*location**=**'global'*,*header_provider**=**None*)¶**
Bases:object

Registry that provides McpToolsets for MCP servers registered in API Registry.

Initialize the API Registry.


**Parameters:**
**api_registry_project_id**– The project ID for the Google Cloud API Registry.

**location**– The location of the API Registry resources.

**header_provider**– Optional function to provide additional headers for MCP server calls.


**get_toolset(*mcp_server_name*,*tool_filter**=**None*,*tool_name_prefix**=**None*)¶**
Return the MCP Toolset based on the params.


**Return type:**
[McpToolset


**Parameters:**
**mcp_server_name**– Filter to select the MCP server name to get tools from.

**tool_filter**– Optional filter to select specific tools. Can be a list of tool names or a ToolPredicate function.

**tool_name_prefix**– Optional prefix to prepend to the names of the tools returned by the toolset.


**Returns:**
A toolset for the MCP server specified.


**Return type:**
[McpToolset


***pydantic**model*google.adk.tools.AuthToolArguments¶**
Bases:BaseModelWithConfig

the arguments for the special long running function tool that is used to

request end user credentials.