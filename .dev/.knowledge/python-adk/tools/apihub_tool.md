# google.adk.tools.apihub_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.apihub_tool)

---


google.adk.tools.apihub_tool module


class google.adk.tools.apihub_tool.APIHubToolset(*, apihub_resource_name, access_token=None, service_account_json=None, name='', description='', lazy_load_spec=False, auth_scheme=None, auth_credential=None, apihub_client=None, tool_filter=None)
Bases: BaseToolset
APIHubTool generates tools from a given API Hub resource.
Examples:
apihub_toolset = APIHubToolset(
    apihub_resource_name="projects/test-project/locations/us-central1/apis/test-api",
    service_account_json="...",
    tool_filter=lambda tool, ctx=None: tool.name in ('my_tool',
    'my_other_tool')
)

# Get all available tools
agent = LlmAgent(tools=apihub_toolset)


apihub_resource_name is the resource name from API Hub. It must include
API name, and can optionally include API version and spec name.

If apihub_resource_name includes a spec resource name, the content of that
spec will be used for generating the tools.
If apihub_resource_name includes only an api or a version name, the
first spec of the first version of that API will be used.

Initializes the APIHubTool with the given parameters.
Examples:
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


apihub_resource_name is the resource name from API Hub. It must include
API name, and can optionally include API version and spec name.

If apihub_resource_name includes a spec resource name, the content of that
spec will be used for generating the tools.
If apihub_resource_name includes only an api or a version name, the
first spec of the first version of that API will be used.

Example:

projects/xxx/locations/us-central1/apis/apiname/…
https://console.cloud.google.com/apigee/api-hub/apis/apiname?project=xxx


Parameters:

apihub_resource_name – The resource name of the API in API Hub.
Example: projects/test-project/locations/us-central1/apis/test-api.
access_token – Google Access token. Generate with gcloud cli
gcloud auth print-access-token. Used for fetching API Specs from API Hub.
service_account_json – The service account config as a json string.
Required if not using default service credential. It is used for
creating the API Hub client and fetching the API Specs from API Hub.
apihub_client – Optional custom API Hub client.
name – Name of the toolset. Optional.
description – Description of the toolset. Optional.
auth_scheme – Auth scheme that applies to all the tool in the toolset.
auth_credential – Auth credential that applies to all the tool in the
toolset.
lazy_load_spec – If True, the spec will be loaded lazily when needed.
Otherwise, the spec will be loaded immediately and the tools will be
generated during initialization.
tool_filter – The filter used to filter the tools in the toolset. It can
be either a tool predicate or a list of tool names of the tools to
expose.





async close()
Performs cleanup and releases resources held by the toolset.

Note
This method is invoked, for example, at the end of an agent server’s
lifecycle or when the toolset is no longer needed. Implementations
should ensure that any open connections, files, or other managed
resources are properly released to prevent leaks.





get_auth_config()
Returns the auth config for this toolset.
ADK will populate exchanged_auth_credential on this config before calling
get_tools(). The toolset can then access the ready-to-use credential via
self._auth_config.exchanged_auth_credential.

Return type:
Optional[AuthConfig]






async get_tools(readonly_context=None)
Retrieves all available tools.

Return type:
List[RestApiTool]

Returns:
A list of all available RestApiTool objects.







