# google.adk.tools.application_integration_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.application_integration_tool)

---


google.adk.tools.application_integration_tool module


class google.adk.tools.application_integration_tool.ApplicationIntegrationToolset(project, location, connection_template_override=None, integration=None, triggers=None, connection=None, entity_operations=None, actions=None, tool_name_prefix='', tool_instructions='', service_account_json=None, auth_scheme=None, auth_credential=None, tool_filter=None)
Bases: BaseToolset
ApplicationIntegrationToolset generates tools from a given Application
Integration or Integration Connector resource.
Example Usage:
# Get all available tools for an integration with api trigger
application_integration_toolset = ApplicationIntegrationToolset(
    project="test-project",
    location="us-central1"
    integration="test-integration",
    triggers=["api_trigger/test_trigger"],
    service_account_credentials={...},
)

# Get all available tools for a connection using entity operations and
# actions
# Note: Find the list of supported entity operations and actions for a
# connection using integration connector apis:
# https://cloud.google.com/integration-connectors/docs/reference/rest/v1/projects.locations.connections.connectionSchemaMetadata
application_integration_toolset = ApplicationIntegrationToolset(
    project="test-project",
    location="us-central1"
    connection="test-connection",
    entity_operations=["EntityId1": ["LIST","CREATE"], "EntityId2": []],
    #empty list for actions means all operations on the entity are supported
    actions=["action1"],
    service_account_credentials={...},
)

# Feed the toolset to agent
agent = LlmAgent(tools=[
    ...,
    application_integration_toolset,
])


Args:

Parameters:

project – The GCP project ID.
location – The GCP location.
connection_template_override – Overrides ExecuteConnection default
integration name.
integration – The integration name.
triggers – The list of trigger names in the integration.
connection – The connection name.
entity_operations – The entity operations supported by the connection.
actions – The actions supported by the connection.
tool_name_prefix – The name prefix of the generated tools.
tool_instructions – The instructions for the tool.
service_account_json – The service account configuration as a dictionary.
Required if not using default service credential. Used for fetching
the Application Integration or Integration Connector resource.
tool_filter – The filter used to filter the tools in the toolset. It can
be either a tool predicate or a list of tool names of the tools to
expose.


Raises:

ValueError – If none of the following conditions are met:
    - integration is provided.
    - connection is provided and at least one of entity_operations
      or actions is provided.
Exception – If there is an error during the initialization of the
    integration or connection client.





async close()
Performs cleanup and releases resources held by the toolset.

Return type:
None



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
Return all tools in the toolset based on the provided context.

Return type:
List[RestApiTool]

Parameters:
readonly_context (ReadonlyContext, optional) – Context used to filter tools
available to the agent. If None, all tools in the toolset are returned.

Returns:
A list of tools available under the specified context.

Return type:
list[BaseTool]








class google.adk.tools.application_integration_tool.IntegrationConnectorTool(name, description, connection_name, connection_host, connection_service_name, entity, operation, action, rest_api_tool, auth_scheme=None, auth_credential=None)
Bases: BaseTool
A tool that wraps a RestApiTool to interact with a specific Application Integration endpoint.
This tool adds Application Integration specific context like connection
details, entity, operation, and action to the underlying REST API call
handled by RestApiTool. It prepares the arguments and then delegates the
actual API call execution to the contained RestApiTool instance.

Generates request params and body
Attaches auth credentials to API call.

Example:
# Each API operation in the spec will be turned into its own tool
# Name of the tool is the operationId of that operation, in snake case
operations = OperationGenerator().parse(openapi_spec_dict)
tool = [RestApiTool.from_parsed_operation(o) for o in operations]


Initializes the ApplicationIntegrationTool.

Parameters:

name – The name of the tool, typically derived from the API operation.
Should be unique and adhere to Gemini function naming conventions
(e.g., less than 64 characters).
description – A description of what the tool does, usually based on the
API operation’s summary or description.
connection_name – The name of the Integration Connector connection.
connection_host – The hostname or IP address for the connection.
connection_service_name – The specific service name within the host.
entity – The Integration Connector entity being targeted.
operation – The specific operation being performed on the entity.
action – The action associated with the operation (e.g., ‘execute’).
rest_api_tool – An initialized RestApiTool instance that handles the
underlying REST API communication based on an OpenAPI specification
operation. This tool will be called by ApplicationIntegrationTool with
added connection and context arguments. tool =
[RestApiTool.from_parsed_operation(o) for o in operations]





EXCLUDE_FIELDS = ['connection_name', 'service_name', 'host', 'entity', 'operation', 'action', 'dynamic_auth_config']




OPTIONAL_FIELDS = ['page_size', 'page_token', 'filter', 'sortByColumns']




async run_async(*, args, tool_context)
Runs the tool with the given arguments and context.

Return type:
Dict[str, Any]



Note

Required if this tool needs to run at the client side.
Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for
Gemini.



Parameters:

args – The LLM-filled arguments.
tool_context – The context of the tool.


Returns:
The result of running the tool.







