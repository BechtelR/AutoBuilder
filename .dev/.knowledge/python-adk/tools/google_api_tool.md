# google.adk.tools.google_api_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.google_api_tool)

---


google.adk.tools.google_api_tool module
Auto-generated tools and toolsets for Google APIs.
These tools and toolsets are auto-generated based on the API specifications
provided by the Google API Discovery API.


class google.adk.tools.google_api_tool.BigQueryToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated BigQuery toolset based on Google BigQuery API v2 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







class google.adk.tools.google_api_tool.CalendarToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated Calendar toolset based on Google Calendar API v3 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







class google.adk.tools.google_api_tool.DocsToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated Docs toolset based on Google Docs API v1 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







class google.adk.tools.google_api_tool.GmailToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated Gmail toolset based on Google Gmail API v1 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







class google.adk.tools.google_api_tool.GoogleApiTool(rest_api_tool, client_id=None, client_secret=None, service_account=None, *, additional_headers=None)
Bases: BaseTool


configure_auth(client_id, client_secret)




configure_sa_auth(service_account)




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








class google.adk.tools.google_api_tool.GoogleApiToolset(api_name, api_version, client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None, *, additional_headers=None)
Bases: BaseToolset
Google API Toolset contains tools for interacting with Google APIs.
Usually one toolsets will contain tools only related to one Google API, e.g.
Google Bigquery API toolset will contain tools only related to Google
Bigquery API, like list dataset tool, list table tool etc.

Parameters:

api_name – The name of the Google API (e.g., “calendar”, “gmail”).
api_version – The version of the API (e.g., “v3”, “v1”).
client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.
additional_headers – Optional dict of HTTP headers to inject into every request
executed by this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.





async close()
Performs cleanup and releases resources held by the toolset.

Note
This method is invoked, for example, at the end of an agent server’s
lifecycle or when the toolset is no longer needed. Implementations
should ensure that any open connections, files, or other managed
resources are properly released to prevent leaks.





configure_auth(client_id, client_secret)




configure_sa_auth(service_account)




async get_tools(readonly_context=None)
Get all tools in the toolset.

Return type:
List[GoogleApiTool]






set_tool_filter(tool_filter)






class google.adk.tools.google_api_tool.SheetsToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated Sheets toolset based on Google Sheets API v4 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







class google.adk.tools.google_api_tool.SlidesToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated Slides toolset based on Google Slides API v1 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







class google.adk.tools.google_api_tool.YoutubeToolset(client_id=None, client_secret=None, tool_filter=None, service_account=None, tool_name_prefix=None)
Bases: GoogleApiToolset
Auto-generated YouTube toolset based on YouTube API v3 spec exposed by Google API discovery API.

Parameters:

client_id – OAuth2 client ID for authentication.
client_secret – OAuth2 client secret for authentication.
tool_filter – Optional filter to include only specific tools or use a predicate function.
service_account – Optional service account for authentication.
tool_name_prefix – Optional prefix to add to all tool names in this toolset.



Initialize the toolset.

Parameters:

tool_filter – Filter to apply to tools.
tool_name_prefix – The prefix to prepend to the names of the tools returned by the toolset.







google.adk.tools.google_maps_grounding_tool module


class google.adk.tools.google_maps_grounding_tool.GoogleMapsGroundingTool
Bases: BaseTool
A built-in tool that is automatically invoked by Gemini 2 models to ground query results with Google Maps.
This tool operates internally within the model and does not require or perform
local code execution.
Only available for use with the VertexAI Gemini API (e.g.
GOOGLE_GENAI_USE_VERTEXAI=TRUE)


async process_llm_request(*, tool_context, llm_request)
Processes the outgoing LLM request for this tool.
Use cases:
- Most common use case is adding this tool to the LLM request.
- Some tools may just preprocess the LLM request before it’s sent out.

Return type:
None

Parameters:

tool_context – The context of the tool.
llm_request – The outgoing LLM request, mutable this method.








