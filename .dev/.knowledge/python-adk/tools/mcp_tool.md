# google.adk.tools.mcp_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.mcp_tool)

---


google.adk.tools.mcp_tool module


class google.adk.tools.mcp_tool.MCPTool(*args, **kwargs)
Bases: McpTool
Deprecated name, use McpTool instead.
Initializes an McpTool.
This tool wraps an MCP Tool interface and uses a session manager to
communicate with the MCP server.

Parameters:

mcp_tool – The MCP tool to wrap.
mcp_session_manager – The MCP session manager to use for communication.
auth_scheme – The authentication scheme to use.
auth_credential – The authentication credential to use.
require_confirmation – Whether this tool requires confirmation. A boolean
or a callable that takes the function’s arguments and returns a
boolean. If the callable returns True, the tool will require
confirmation from the user.


Raises:
ValueError – If mcp_tool or mcp_session_manager is None.






class google.adk.tools.mcp_tool.MCPToolset(*args, **kwargs)
Bases: McpToolset
Deprecated name, use McpToolset instead.
Initializes the McpToolset.

Parameters:

connection_params – The connection parameters to the MCP server. Can be:
StdioConnectionParams for using local mcp server (e.g. using npx or
python3); or SseConnectionParams for a local/remote SSE server; or
StreamableHTTPConnectionParams for local/remote Streamable http
server. Note, StdioServerParameters is also supported for using local
mcp server (e.g. using npx or python3 ), but it does not support
timeout, and we recommend to use StdioConnectionParams instead when
timeout is needed.
tool_filter – Optional filter to select specific tools. Can be either: - A
list of tool names to include - A ToolPredicate function for custom
filtering logic
tool_name_prefix – A prefix to be added to the name of each tool in this
toolset.
errlog – TextIO stream for error logging.
auth_scheme – The auth scheme of the tool for tool calling
auth_credential – The auth credential of the tool for tool calling
require_confirmation – Whether tools in this toolset require
confirmation. Can be a single boolean or a callable to apply to all
tools.
header_provider – A callable that takes a ReadonlyContext and returns a
dictionary of headers to be used for the MCP session.







class google.adk.tools.mcp_tool.McpTool(*, mcp_tool, mcp_session_manager, auth_scheme=None, auth_credential=None, require_confirmation=False, header_provider=None)
Bases: BaseAuthenticatedTool
Turns an MCP Tool into an ADK Tool.
Internally, the tool initializes from a MCP Tool, and uses the MCP Session to
call the tool.
Note: For API key authentication, only header-based API keys are supported.
Query and cookie-based API keys will result in authentication errors.
Initializes an McpTool.
This tool wraps an MCP Tool interface and uses a session manager to
communicate with the MCP server.

Parameters:

mcp_tool – The MCP tool to wrap.
mcp_session_manager – The MCP session manager to use for communication.
auth_scheme – The authentication scheme to use.
auth_credential – The authentication credential to use.
require_confirmation – Whether this tool requires confirmation. A boolean
or a callable that takes the function’s arguments and returns a
boolean. If the callable returns True, the tool will require
confirmation from the user.


Raises:
ValueError – If mcp_tool or mcp_session_manager is None.




property raw_mcp_tool: Tool
Returns the raw MCP tool.




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








class google.adk.tools.mcp_tool.McpToolset(*, connection_params, tool_filter=None, tool_name_prefix=None, errlog=<_io.TextIOWrapper name='<stderr>' mode='w' encoding='utf-8'>, auth_scheme=None, auth_credential=None, require_confirmation=False, header_provider=None)
Bases: BaseToolset
Connects to a MCP Server, and retrieves MCP Tools into ADK Tools.
This toolset manages the connection to an MCP server and provides tools
that can be used by an agent. It properly implements the BaseToolset
interface for easy integration with the agent framework.
Usage:
toolset = McpToolset(
    connection_params=StdioServerParameters(
        command='npx',
        args=["-y", "@modelcontextprotocol/server-filesystem"],
    ),
    tool_filter=['read_file', 'list_directory']  # Optional: filter specific tools
)

# Use in an agent
agent = LlmAgent(
    model='gemini-2.0-flash',
    name='enterprise_assistant',
    instruction='Help user accessing their file systems',
    tools=[toolset],
)

# Cleanup is handled automatically by the agent framework
# But you can also manually close if needed:
# await toolset.close()


Initializes the McpToolset.

Parameters:

connection_params – The connection parameters to the MCP server. Can be:
StdioConnectionParams for using local mcp server (e.g. using npx or
python3); or SseConnectionParams for a local/remote SSE server; or
StreamableHTTPConnectionParams for local/remote Streamable http
server. Note, StdioServerParameters is also supported for using local
mcp server (e.g. using npx or python3 ), but it does not support
timeout, and we recommend to use StdioConnectionParams instead when
timeout is needed.
tool_filter – Optional filter to select specific tools. Can be either: - A
list of tool names to include - A ToolPredicate function for custom
filtering logic
tool_name_prefix – A prefix to be added to the name of each tool in this
toolset.
errlog – TextIO stream for error logging.
auth_scheme – The auth scheme of the tool for tool calling
auth_credential – The auth credential of the tool for tool calling
require_confirmation – Whether tools in this toolset require
confirmation. Can be a single boolean or a callable to apply to all
tools.
header_provider – A callable that takes a ReadonlyContext and returns a
dictionary of headers to be used for the MCP session.





async close()
Performs cleanup and releases resources held by the toolset.
This method closes the MCP session and cleans up all associated resources.
It’s designed to be safe to call multiple times and handles cleanup errors
gracefully to avoid blocking application shutdown.

Return type:
None






classmethod from_config(config, config_abs_path)
Creates an McpToolset from a configuration object.

Return type:
McpToolset






get_auth_config()
Returns the auth config for this toolset.
ADK will populate exchanged_auth_credential on this config before calling
get_tools(). The toolset can then access the ready-to-use credential via
self._auth_config.exchanged_auth_credential.

Return type:
Optional[AuthConfig]






async get_resource_info(name, readonly_context=None)
Returns metadata about a specific resource (name, MIME type, etc.).

Return type:
dict[str, Any]






async get_tools(readonly_context=None)
Return all tools in the toolset based on the provided context.

Return type:
List[BaseTool]

Parameters:
readonly_context – Context used to filter tools available to the agent.
If None, all tools in the toolset are returned.

Returns:
A list of tools available under the specified context.

Return type:
List[BaseTool]






async list_resources(readonly_context=None)
Returns a list of resource names available on the MCP server.

Return type:
list[str]






async read_resource(name, readonly_context=None)
Fetches and returns a list of contents of the named resource.

Return type:
Any

Parameters:

name – The name of the resource to fetch.
readonly_context – Context used to provide headers for the MCP session.


Returns:
List of contents of the resource.








pydantic model google.adk.tools.mcp_tool.SseConnectionParams
Bases: BaseModel
Parameters for the MCP SSE connection.
See MCP SSE Client documentation for more details.
https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/sse.py


url
URL for the MCP SSE server.




headers
Headers for the MCP SSE connection.




timeout
Timeout in seconds for establishing the connection to the MCP SSE
server.




sse_read_timeout
Timeout in seconds for reading data from the MCP SSE
server.



Show JSON schema{
   "title": "SseConnectionParams",
   "description": "Parameters for the MCP SSE connection.\n\nSee MCP SSE Client documentation for more details.\nhttps://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/sse.py\n\nAttributes:\n    url: URL for the MCP SSE server.\n    headers: Headers for the MCP SSE connection.\n    timeout: Timeout in seconds for establishing the connection to the MCP SSE\n      server.\n    sse_read_timeout: Timeout in seconds for reading data from the MCP SSE\n      server.",
   "type": "object",
   "properties": {
      "url": {
         "title": "Url",
         "type": "string"
      },
      "headers": {
         "anyOf": [
            {
               "additionalProperties": true,
               "type": "object"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Headers"
      },
      "timeout": {
         "default": 5.0,
         "title": "Timeout",
         "type": "number"
      },
      "sse_read_timeout": {
         "default": 300.0,
         "title": "Sse Read Timeout",
         "type": "number"
      }
   },
   "required": [
      "url"
   ]
}



Fields:

headers (dict[str, Any] | None)
sse_read_timeout (float)
timeout (float)
url (str)





field headers: dict[str, Any] | None = None




field sse_read_timeout: float = 300.0




field timeout: float = 5.0




field url: str [Required]






pydantic model google.adk.tools.mcp_tool.StdioConnectionParams
Bases: BaseModel
Parameters for the MCP Stdio connection.


server_params
Parameters for the MCP Stdio server.




timeout
Timeout in seconds for establishing the connection to the MCP
stdio server.



Show JSON schema{
   "title": "StdioConnectionParams",
   "description": "Parameters for the MCP Stdio connection.\n\nAttributes:\n    server_params: Parameters for the MCP Stdio server.\n    timeout: Timeout in seconds for establishing the connection to the MCP\n      stdio server.",
   "type": "object",
   "properties": {
      "server_params": {
         "$ref": "#/$defs/StdioServerParameters"
      },
      "timeout": {
         "default": 5.0,
         "title": "Timeout",
         "type": "number"
      }
   },
   "$defs": {
      "StdioServerParameters": {
         "properties": {
            "command": {
               "title": "Command",
               "type": "string"
            },
            "args": {
               "items": {
                  "type": "string"
               },
               "title": "Args",
               "type": "array"
            },
            "env": {
               "anyOf": [
                  {
                     "additionalProperties": {
                        "type": "string"
                     },
                     "type": "object"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Env"
            },
            "cwd": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "format": "path",
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Cwd"
            },
            "encoding": {
               "default": "utf-8",
               "title": "Encoding",
               "type": "string"
            },
            "encoding_error_handler": {
               "default": "strict",
               "enum": [
                  "strict",
                  "ignore",
                  "replace"
               ],
               "title": "Encoding Error Handler",
               "type": "string"
            }
         },
         "required": [
            "command"
         ],
         "title": "StdioServerParameters",
         "type": "object"
      }
   },
   "required": [
      "server_params"
   ]
}



Fields:

server_params (mcp.client.stdio.StdioServerParameters)
timeout (float)





field server_params: StdioServerParameters [Required]




field timeout: float = 5.0






pydantic model google.adk.tools.mcp_tool.StreamableHTTPConnectionParams
Bases: BaseModel
Parameters for the MCP Streamable HTTP connection.
See MCP Streamable HTTP Client documentation for more details.
https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/streamable_http.py


url
URL for the MCP Streamable HTTP server.




headers
Headers for the MCP Streamable HTTP connection.




timeout
Timeout in seconds for establishing the connection to the MCP
Streamable HTTP server.




sse_read_timeout
Timeout in seconds for reading data from the MCP
Streamable HTTP server.




terminate_on_close
Whether to terminate the MCP Streamable HTTP server
when the connection is closed.




httpx_client_factory
Factory function to create a custom HTTPX client. If
not provided, a default factory will be used.



Show JSON schema{
   "title": "StreamableHTTPConnectionParams",
   "type": "object",
   "properties": {
      "url": {
         "title": "Url",
         "type": "string"
      },
      "headers": {
         "anyOf": [
            {
               "additionalProperties": true,
               "type": "object"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Headers"
      },
      "timeout": {
         "default": 5.0,
         "title": "Timeout",
         "type": "number"
      },
      "sse_read_timeout": {
         "default": 300.0,
         "title": "Sse Read Timeout",
         "type": "number"
      },
      "terminate_on_close": {
         "default": true,
         "title": "Terminate On Close",
         "type": "boolean"
      },
      "httpx_client_factory": {
         "default": null,
         "title": "Httpx Client Factory"
      }
   },
   "required": [
      "url"
   ]
}



Fields:

headers (dict[str, Any] | None)
httpx_client_factory (google.adk.tools.mcp_tool.mcp_session_manager.CheckableMcpHttpClientFactory)
sse_read_timeout (float)
terminate_on_close (bool)
timeout (float)
url (str)





field headers: dict[str, Any] | None = None




field httpx_client_factory: CheckableMcpHttpClientFactory = <function create_mcp_http_client>




field sse_read_timeout: float = 300.0




field terminate_on_close: bool = True




field timeout: float = 5.0




field url: str [Required]






google.adk.tools.mcp_tool.adk_to_mcp_tool_type(tool)
Convert a Tool in ADK into MCP tool type.
This function transforms an ADK tool definition into its equivalent
representation in the MCP (Model Context Protocol) system.

Return type:
Tool

Parameters:
tool – The ADK tool to convert. It should be an instance of a class derived
from BaseTool.

Returns:
An object of MCP Tool type, representing the converted tool.


Examples
# Assuming ‘my_tool’ is an instance of a BaseTool derived class
mcp_tool = adk_to_mcp_tool_type(my_tool)
print(mcp_tool)




google.adk.tools.mcp_tool.gemini_to_json_schema(gemini_schema)
Converts a Gemini Schema object into a JSON Schema dictionary.

Return type:
Dict[str, Any]

Parameters:
gemini_schema – An instance of the Gemini Schema class.

Returns:
A dictionary representing the equivalent JSON Schema.

Raises:

TypeError – If the input is not an instance of the expected Schema class.
ValueError – If an invalid Gemini Type enum value is encountered.






