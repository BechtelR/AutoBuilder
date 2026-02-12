# google.adk.tools.openapi_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.openapi_tool)

---


google.adk.tools.openapi_tool module


class google.adk.tools.openapi_tool.OpenAPIToolset(*, spec_dict=None, spec_str=None, spec_str_type='json', auth_scheme=None, auth_credential=None, credential_key=None, tool_filter=None, tool_name_prefix=None, ssl_verify=None, header_provider=None)
Bases: BaseToolset
Class for parsing OpenAPI spec into a list of RestApiTool.
Usage:
# Initialize OpenAPI toolset from a spec string.
openapi_toolset = OpenAPIToolset(spec_str=openapi_spec_str,
  spec_str_type="json")
# Or, initialize OpenAPI toolset from a spec dictionary.
openapi_toolset = OpenAPIToolset(spec_dict=openapi_spec_dict)

# Add all tools to an agent.
agent = Agent(
  tools=[*openapi_toolset.get_tools()]
)
# Or, add a single tool to an agent.
agent = Agent(
  tools=[openapi_toolset.get_tool('tool_name')]
)


Initializes the OpenAPIToolset.
Usage:
# Initialize OpenAPI toolset from a spec string.
openapi_toolset = OpenAPIToolset(spec_str=openapi_spec_str,
  spec_str_type="json")
# Or, initialize OpenAPI toolset from a spec dictionary.
openapi_toolset = OpenAPIToolset(spec_dict=openapi_spec_dict)

# Add all tools to an agent.
agent = Agent(
  tools=[*openapi_toolset.get_tools()]
)
# Or, add a single tool to an agent.
agent = Agent(
  tools=[openapi_toolset.get_tool('tool_name')]
)



Parameters:

spec_dict – The OpenAPI spec dictionary. If provided, it will be used
instead of loading the spec from a string.
spec_str – The OpenAPI spec string in JSON or YAML format. It will be used
when spec_dict is not provided.
spec_str_type – The type of the OpenAPI spec string. Can be “json” or
“yaml”.
auth_scheme – The auth scheme to use for all tools. Use AuthScheme or use
helpers in google.adk.tools.openapi_tool.auth.auth_helpers
auth_credential – The auth credential to use for all tools. Use
AuthCredential or use helpers in
google.adk.tools.openapi_tool.auth.auth_helpers
credential_key – Optional stable key used for interactive auth and
credential caching across all tools in this toolset.
tool_filter – The filter used to filter the tools in the toolset. It can be
either a tool predicate or a list of tool names of the tools to expose.
tool_name_prefix – The prefix to prepend to the names of the tools returned
by the toolset. Useful when multiple OpenAPI specs have tools with
similar names.
ssl_verify – SSL certificate verification option for all tools. Can be:
- None: Use default verification (True)
- True: Verify SSL certificates using system CA
- False: Disable SSL verification (insecure, not recommended)
- str: Path to a CA bundle file or directory for custom CA
- ssl.SSLContext: Custom SSL context for advanced configuration
This is useful for enterprise environments where requests go through
a TLS-intercepting proxy with a custom CA certificate.
header_provider – A callable that returns a dictionary of headers to be
included in API requests. The callable receives the ReadonlyContext as
an argument, allowing dynamic header generation based on the current
context. Useful for adding custom headers like correlation IDs,
authentication tokens, or other request metadata.





async close()
Performs cleanup and releases resources held by the toolset.

Note
This method is invoked, for example, at the end of an agent server’s
lifecycle or when the toolset is no longer needed. Implementations
should ensure that any open connections, files, or other managed
resources are properly released to prevent leaks.





configure_ssl_verify_all(ssl_verify=None)
Configure SSL certificate verification for all tools.
This is useful for enterprise environments where requests go through a
TLS-intercepting proxy with a custom CA certificate.

Parameters:
ssl_verify – SSL certificate verification option. Can be:
- None: Use default verification (True)
- True: Verify SSL certificates using system CA
- False: Disable SSL verification (insecure, not recommended)
- str: Path to a CA bundle file or directory for custom CA
- ssl.SSLContext: Custom SSL context for advanced configuration






get_auth_config()
Returns the auth config for this toolset.
Note: This returns a copy so any exchanged credentials populated by the ADK
framework do not persist on the toolset instance across invocations.

Return type:
Optional[AuthConfig]






get_tool(tool_name)
Get a tool by name.

Return type:
Optional[RestApiTool]






async get_tools(readonly_context=None)
Get all tools in the toolset.

Return type:
List[RestApiTool]








class google.adk.tools.openapi_tool.RestApiTool(name, description, endpoint, operation, auth_scheme=None, auth_credential=None, should_parse_operation=True, ssl_verify=None, header_provider=None, *, credential_key=None)
Bases: BaseTool
A generic tool that interacts with a REST API.

Generates request params and body
Attaches auth credentials to API call.

Example:
# Each API operation in the spec will be turned into its own tool
# Name of the tool is the operationId of that operation, in snake case
operations = OperationGenerator().parse(openapi_spec_dict)
tool = [RestApiTool.from_parsed_operation(o) for o in operations]


Initializes the RestApiTool with the given parameters.
To generate RestApiTool from OpenAPI Specs, use OperationGenerator.
Example:
# Each API operation in the spec will be turned into its own tool
# Name of the tool is the operationId of that operation, in snake case
operations = OperationGenerator().parse(openapi_spec_dict)
tool = [RestApiTool.from_parsed_operation(o) for o in operations]


Hint: Use google.adk.tools.openapi_tool.auth.auth_helpers to construct
auth_scheme and auth_credential.

Parameters:

name – The name of the tool.
description – The description of the tool.
endpoint – Include the base_url, path, and method of the tool.
operation – Pydantic object or a dict. Representing the OpenAPI Operation
object
(https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#operation-object)
auth_scheme – The auth scheme of the tool. Representing the OpenAPI
SecurityScheme object
(https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#security-scheme-object)
auth_credential – The authentication credential of the tool.
should_parse_operation – Whether to parse the operation.
ssl_verify – SSL certificate verification option. Can be:
- None: Use default verification
- True: Verify SSL certificates using system CA
- False: Disable SSL verification (insecure, not recommended)
- str: Path to a CA bundle file or directory for custom CA
- ssl.SSLContext: Custom SSL context for advanced configuration
header_provider – A callable that returns a dictionary of headers to be
included in API requests. The callable receives the ReadonlyContext as
an argument, allowing dynamic header generation based on the current
context. Useful for adding custom headers like correlation IDs,
authentication tokens, or other request metadata.
credential_key – Optional stable key used for interactive auth and
credential caching.





async call(*, args, tool_context)
Executes the REST API call.

Return type:
Dict[str, Any]

Parameters:

args – Keyword arguments representing the operation parameters.
tool_context – The tool context (not used here, but required by the
interface).


Returns:
The API response as a dictionary.






configure_auth_credential(auth_credential=None)
Configures the authentication credential for the API call.

Parameters:
auth_credential – AuthCredential|dict - The authentication credential.
The dict is converted to an AuthCredential object.






configure_auth_scheme(auth_scheme)
Configures the authentication scheme for the API call.

Parameters:
auth_scheme – AuthScheme|dict -: The authentication scheme. The dict is
converted to a AuthScheme object.






configure_credential_key(credential_key=None)
Configures the credential key for interactive auth / caching.




configure_ssl_verify(ssl_verify=None)
Configures SSL certificate verification for the API call.
This is useful for enterprise environments where requests go through a
TLS-intercepting proxy with a custom CA certificate.

Parameters:
ssl_verify – SSL certificate verification option. Can be:
- None: Use default verification (True)
- True: Verify SSL certificates using system CA
- False: Disable SSL verification (insecure, not recommended)
- str: Path to a CA bundle file or directory for custom CA
- ssl.SSLContext: Custom SSL context for advanced configuration






classmethod from_parsed_operation(parsed, ssl_verify=None, header_provider=None)
Initializes the RestApiTool from a ParsedOperation object.

Return type:
RestApiTool

Parameters:

parsed – A ParsedOperation object.
ssl_verify – SSL certificate verification option.
header_provider – A callable that returns a dictionary of headers to be
included in API requests. The callable receives the ReadonlyContext as
an argument, allowing dynamic header generation based on the current
context. Useful for adding custom headers like correlation IDs,
authentication tokens, or other request metadata.


Returns:
A RestApiTool object.






classmethod from_parsed_operation_str(parsed_operation_str)
Initializes the RestApiTool from a dict.

Return type:
RestApiTool

Parameters:
parsed – A dict representation of a ParsedOperation object.

Returns:
A RestApiTool object.






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






set_default_headers(headers)
Sets default headers that are merged into every request.





