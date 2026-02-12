# google.adk.planners module¶

***class*google.adk.planners.BasePlanner¶**
Bases:ABC

Abstract base class for all planners.

The planner allows the agent to generate plans for the queries to guide its action.


***abstractmethod*build_planning_instruction(*readonly_context*,*llm_request*)¶**
Builds the system instruction to be appended to the LLM request for planning.


**Return type:**
Optional[str]


**Parameters:**
**readonly_context**– The readonly context of the invocation.

**llm_request**– The LLM request. Readonly.


**Returns:**
The planning system instruction, or None if no instruction is needed.


***abstractmethod*process_planning_response(*callback_context*,*response_parts*)¶**
Processes the LLM response for planning.


**Return type:**
Optional[List[Part]]


**Parameters:**
**callback_context**– The callback context of the invocation.

**response_parts**– The LLM response parts. Readonly.


**Returns:**
The processed response parts, or None if no processing is needed.


***class*google.adk.planners.BuiltInPlanner(***,*thinking_config*)¶**
Bases:[BasePlanner

The built-in planner that uses model’s built-in thinking features.


**thinking_config¶**
Config for model built-in thinking features. An error will be returned if this field is set for models that don’t support thinking.

Initializes the built-in planner.


**Parameters:**
**thinking_config**– Config for model built-in thinking features. An error will be returned if this field is set for models that don’t support thinking.


**apply_thinking_config(*llm_request*)¶**
Applies the thinking config to the LLM request.


**Return type:**
None


**Parameters:**
**llm_request**– The LLM request to apply the thinking config to.


**build_planning_instruction(*readonly_context*,*llm_request*)¶**
Builds the system instruction to be appended to the LLM request for planning.


**Return type:**
Optional[str]


**Parameters:**
**readonly_context**– The readonly context of the invocation.

**llm_request**– The LLM request. Readonly.


**Returns:**
The planning system instruction, or None if no instruction is needed.


**process_planning_response(*callback_context*,*response_parts*)¶**
Processes the LLM response for planning.


**Return type:**
Optional[List[Part]]


**Parameters:**
**callback_context**– The callback context of the invocation.

**response_parts**– The LLM response parts. Readonly.


**Returns:**
The processed response parts, or None if no processing is needed.


**thinking_config*:**ThinkingConfig*¶**
Config for model built-in thinking features. An error will be returned if this field is set for models that don’t support thinking.


***class*google.adk.planners.PlanReActPlanner¶**
Bases:[BasePlanner

Plan-Re-Act planner that constrains the LLM response to generate a plan before any action/observation.

Note: this planner does not require the model to support built-in thinking features or setting the thinking config.


**build_planning_instruction(*readonly_context*,*llm_request*)¶**
Builds the system instruction to be appended to the LLM request for planning.


**Return type:**
str


**Parameters:**
**readonly_context**– The readonly context of the invocation.

**llm_request**– The LLM request. Readonly.


**Returns:**
The planning system instruction, or None if no instruction is needed.


**process_planning_response(*callback_context*,*response_parts*)¶**
Processes the LLM response for planning.


**Return type:**
Optional[List[Part]]


**Parameters:**
**callback_context**– The callback context of the invocation.

**response_parts**– The LLM response parts. Readonly.


**Returns:**
The processed response parts, or None if no processing is needed.


# google.adk.platform module¶

# google.adk.plugins module¶

***class*google.adk.plugins.BasePlugin(*name*)¶**
Bases:ABC

Base class for creating plugins.

Plugins provide a structured way to intercept and modify agent, tool, and LLM behaviors at critical execution points in a callback manner. While agent callbacks apply to a particular agent, plugins applies globally to all agents added in the runner. Plugins are best used for adding custom behaviors like logging, monitoring, caching, or modifying requests and responses at key stages.

A plugin can implement one or more methods of callbacks, but should not implement the same method of callback for multiple times.

Relation with [Agent callbacks]([https://google.github.io/adk-docs/callbacks/):

**Execution Order**Similar to Agent callbacks, Plugins are executed in the order they are registered. However, Plugin and Agent Callbacks are executed sequentially, with Plugins takes precedence over agent callbacks. When the callback in a plugin returns a value, it will short circuit all remaining plugins and agent callbacks, causing all remaining plugins and agent callbacks to be skipped.

**Change Propagation**Plugins and agent callbacks can both modify the value of the input parameters, including agent input, tool input, and LLM request/response, etc. They work in the exactly same way. The modifications will be visible and passed to the next callback in the chain. For example, if a plugin modifies the tool input with before_tool_callback, the modified tool input will be passed to the before_tool_callback of the next plugin, and further passed to the agent callbacks if not short-circuited.

To use a plugin, implement the desired callback methods and pass an instance of your custom plugin class to the ADK Runner.

Examples

A simple plugin that logs every tool call.


```
>>> class ToolLoggerPlugin(BasePlugin):
..   def __init__(self):
..     super().__init__(name="tool_logger")
..
..   async def before_tool_callback(
..       self, *, tool: BaseTool, tool_args: dict[str, Any],
tool_context:
ToolContext
..   ):
..     print(f"[{self.name}] Calling tool '{tool.name}' with args:
{tool_args}")
..
..   async def after_tool_callback(
..       self, *, tool: BaseTool, tool_args: dict, tool_context:
ToolContext, result: dict
..   ):
..     print(f"[{self.name}] Tool '{tool.name}' finished with result:
{result}")
..
>>> # Add the plugin to ADK Runner
>>> # runner = Runner(
>>> #     ...
>>> #     plugins=[ToolLoggerPlugin(), AgentPolicyPlugin()],
>>> # )
```

Initializes the plugin.


**Parameters:**
**name**– A unique identifier for this plugin instance.


***async*after_agent_callback(***,*agent*,*callback_context*)¶**
Callback executed after an agent’s primary logic has completed.


**Return type:**
Optional[Content]


**Parameters:**
**agent**– The agent that has just run.

**callback_context**– The context for the agent invocation.


**Returns:**
An optionaltypes.Contentobject. The content to return to the user. When the content is present, the provided content will be used as agent response and appended to event history as agent response.


***async*after_model_callback(***,*callback_context*,*llm_response*)¶**
Callback executed after a response is received from the model.

This is the ideal place to log model responses, collect metrics on token usage, or perform post-processing on the rawLlmResponse.


**Return type:**
Optional[LlmResponse]


**Parameters:**
**callback_context**– The context for the current agent call.

**llm_response**– The response object received from the model.


**Returns:**
An optional value. A non-Nonereturn may be used by the framework to modify or replace the response. ReturningNoneallows the original response to be used.


***async*after_run_callback(***,*invocation_context*)¶**
Callback executed after an ADK runner run has completed.

This is the final callback in the ADK lifecycle, suitable for cleanup, final logging, or reporting tasks.


**Return type:**
None


**Parameters:**
**invocation_context**– The context for the entire invocation.


**Returns:**
None


***async*after_tool_callback(***,*tool*,*tool_args*,*tool_context*,*result*)¶**
Callback executed after a tool has been called.

This callback allows for inspecting, logging, or modifying the result returned by a tool.


**Return type:**
Optional[dict]


**Parameters:**
**tool**– The tool instance that has just been executed.

**tool_args**– The original arguments that were passed to the tool.

**tool_context**– The context specific to the tool execution.

**result**– The dictionary returned by the tool invocation.


**Returns:**
An optional dictionary. If a dictionary is returned, it will**replace**the original result from the tool. This allows for post-processing or altering tool outputs. ReturningNoneuses the original, unmodified result.


***async*before_agent_callback(***,*agent*,*callback_context*)¶**
Callback executed before an agent’s primary logic is invoked.

This callback can be used for logging, setup, or to short-circuit the agent’s execution by returning a value.


**Return type:**
Optional[Content]


**Parameters:**
**agent**– The agent that is about to run.

**callback_context**– The context for the agent invocation.


**Returns:**
An optionaltypes.Contentobject. If a value is returned, it will bypass the agent’s callbacks and its execution, and return this value directly. ReturningNoneallows the agent to proceed normally.


***async*before_model_callback(***,*callback_context*,*llm_request*)¶**
Callback executed before a request is sent to the model.

This provides an opportunity to inspect, log, or modify theLlmRequestobject. It can also be used to implement caching by returning a cachedLlmResponse, which would skip the actual model call.


**Return type:**
Optional[LlmResponse]


**Parameters:**
**callback_context**– The context for the current agent call.

**llm_request**– The prepared request object to be sent to the model.


**Returns:**
An optional value. The interpretation of a non-Nonetrigger an early exit and returns the response immediately. ReturningNoneallows the LLM request to proceed normally.


***async*before_run_callback(***,*invocation_context*)¶**
Callback executed before the ADK runner runs.

This is the first callback to be called in the lifecycle, ideal for global setup or initialization tasks.


**Return type:**
Optional[Content]


**Parameters:**
**invocation_context**– The context for the entire invocation, containing session information, the root agent, etc.


**Returns:**
An optionalEventto be returned to the ADK. Returning a value to halt execution of the runner and ends the runner with that event. ReturnNoneto proceed normally.


***async*before_tool_callback(***,*tool*,*tool_args*,*tool_context*)¶**
Callback executed before a tool is called.

This callback is useful for logging tool usage, input validation, or modifying the arguments before they are passed to the tool.


**Return type:**
Optional[dict]


**Parameters:**
**tool**– The tool instance that is about to be executed.

**tool_args**– The dictionary of arguments to be used for invoking the tool.

**tool_context**– The context specific to the tool execution.


**Returns:**
An optional dictionary. If a dictionary is returned, it will stop the tool execution and return this response immediately. ReturningNoneuses the original, unmodified arguments.


***async*close()¶**
Method executed when the runner is closed.

This method is used for cleanup tasks such as closing network connections or releasing resources.


**Return type:**
None


***async*on_event_callback(***,*invocation_context*,*event*)¶**
Callback executed after an event is yielded from runner.

This is the ideal place to make modification to the event before the event is handled by the underlying agent app.


**Return type:**
Optional[[Event]


**Parameters:**
**invocation_context**– The context for the entire invocation.

**event**– The event raised by the runner.


**Returns:**
An optional value. A non-Nonereturn may be used by the framework to modify or replace the response. ReturningNoneallows the original response to be used.


***async*on_model_error_callback(***,*callback_context*,*llm_request*,*error*)¶**
Callback executed when a model call encounters an error.

This callback provides an opportunity to handle model errors gracefully, potentially providing alternative responses or recovery mechanisms.


**Return type:**
Optional[LlmResponse]


**Parameters:**
**callback_context**– The context for the current agent call.

**llm_request**– The request that was sent to the model when the error occurred.

**error**– The exception that was raised during model execution.


**Returns:**
An optional LlmResponse. If an LlmResponse is returned, it will be used instead of propagating the error. ReturningNoneallows the original error to be raised.


***async*on_tool_error_callback(***,*tool*,*tool_args*,*tool_context*,*error*)¶**
Callback executed when a tool call encounters an error.

This callback provides an opportunity to handle tool errors gracefully, potentially providing alternative responses or recovery mechanisms.


**Return type:**
Optional[dict]


**Parameters:**
**tool**– The tool instance that encountered an error.

**tool_args**– The arguments that were passed to the tool.

**tool_context**– The context specific to the tool execution.

**error**– The exception that was raised during tool execution.


**Returns:**
An optional dictionary. If a dictionary is returned, it will be used as the tool response instead of propagating the error. ReturningNoneallows the original error to be raised.


***async*on_user_message_callback(***,*invocation_context*,*user_message*)¶**
Callback executed when a user message is received before an invocation starts.

This callback helps logging and modifying the user message before the runner starts the invocation.


**Return type:**
Optional[Content]


**Parameters:**
**invocation_context**– The context for the entire invocation.

**user_message**– The message content input by user.


**Returns:**
An optionaltypes.Contentto be returned to the ADK. Returning a value to replace the user message. ReturningNoneto proceed normally.


***class*google.adk.plugins.DebugLoggingPlugin(***,*name**=**'debug_logging_plugin'*,*output_path**=**'adk_debug.yaml'*,*include_session_state**=**True*,*include_system_instruction**=**True*)¶**
Bases:[BasePlugin

A plugin that captures complete debug information to a file.

This plugin records detailed interaction data including: - LLM requests (model, system instruction, contents, tools) - LLM responses (content, usage metadata, errors) - Function calls with arguments - Function responses with results - Events yielded from the runner - Session state at the end of each invocation

The output is written as YAML format for human readability. Each invocation is appended to the file as a separate YAML document (separated by —). This format is easy to read and can be shared for debugging purposes.

Example


```
>>> debug_plugin = DebugLoggingPlugin(output_path="/tmp/adk_debug.yaml")
>>> runner = Runner(
...     agent=my_agent,
...     plugins=[debug_plugin],
... )
```


**output_path¶**
Path to the output file. Defaults to “adk_debug.yaml”.


**include_session_state¶**
Whether to include session state in the output.


**include_system_instruction¶**
Whether to include system instructions.

Initialize the debug logging plugin.


**Parameters:**
**name**– The name of the plugin instance.

**output_path**– Path to the output file. Defaults to “adk_debug.yaml”.

**include_session_state**– Whether to include session state snapshot.

**include_system_instruction**– Whether to include full system instructions.


***async*after_agent_callback(***,*agent*,*callback_context*)¶**
Log agent execution completion.


**Return type:**
Content|None


***async*after_model_callback(***,*callback_context*,*llm_response*)¶**
Log LLM response after receiving from model.


**Return type:**
LlmResponse|None


***async*after_run_callback(***,*invocation_context*)¶**
Finalize and write debug data to file.


**Return type:**
None


***async*after_tool_callback(***,*tool*,*tool_args*,*tool_context*,*result*)¶**
Log tool execution completion.


**Return type:**
dict[str,Any] |None


***async*before_agent_callback(***,*agent*,*callback_context*)¶**
Log agent execution start.


**Return type:**
Content|None


***async*before_model_callback(***,*callback_context*,*llm_request*)¶**
Log LLM request before sending to model.


**Return type:**
LlmResponse|None


***async*before_run_callback(***,*invocation_context*)¶**
Initialize debug state for this invocation.


**Return type:**
Content|None


***async*before_tool_callback(***,*tool*,*tool_args*,*tool_context*)¶**
Log tool execution start.


**Return type:**
dict[str,Any] |None


***async*on_event_callback(***,*invocation_context*,*event*)¶**
Log events yielded from the runner.


**Return type:**
[Event|None


***async*on_model_error_callback(***,*callback_context*,*llm_request*,*error*)¶**
Log LLM error.


**Return type:**
LlmResponse|None


***async*on_tool_error_callback(***,*tool*,*tool_args*,*tool_context*,*error*)¶**
Log tool error.


**Return type:**
dict[str,Any] |None


***async*on_user_message_callback(***,*invocation_context*,*user_message*)¶**
Log user message and invocation start.


**Return type:**
Content|None


***class*google.adk.plugins.LoggingPlugin(*name**=**'logging_plugin'*)¶**
Bases:[BasePlugin

A plugin that logs important information at each callback point.

This plugin helps print all critical events in the console. It is not a replacement of existing logging in ADK. It rather helps terminal based debugging by showing all logs in the console, and serves as a simple demo for everyone to leverage when developing new plugins.

This plugin helps users track the invocation status by logging: - User messages and invocation context - Agent execution flow - LLM requests and responses - Tool calls with arguments and results - Events and final responses - Errors during model and tool execution

Example


```
>>> logging_plugin = LoggingPlugin()
>>> runner = Runner(
...     agents=[my_agent],
...     # ...
...     plugins=[logging_plugin],
... )
```

Initialize the logging plugin.


**Parameters:**
**name**– The name of the plugin instance.


***async*after_agent_callback(***,*agent*,*callback_context*)¶**
Log agent execution completion.


**Return type:**
Optional[Content]


***async*after_model_callback(***,*callback_context*,*llm_response*)¶**
Log LLM response after receiving from model.


**Return type:**
Optional[LlmResponse]


***async*after_run_callback(***,*invocation_context*)¶**
Log invocation completion.


**Return type:**
None


***async*after_tool_callback(***,*tool*,*tool_args*,*tool_context*,*result*)¶**
Log tool execution completion.


**Return type:**
Optional[dict]


***async*before_agent_callback(***,*agent*,*callback_context*)¶**
Log agent execution start.


**Return type:**
Optional[Content]


***async*before_model_callback(***,*callback_context*,*llm_request*)¶**
Log LLM request before sending to model.


**Return type:**
Optional[LlmResponse]


***async*before_run_callback(***,*invocation_context*)¶**
Log invocation start.


**Return type:**
Optional[Content]


***async*before_tool_callback(***,*tool*,*tool_args*,*tool_context*)¶**
Log tool execution start.


**Return type:**
Optional[dict]


***async*on_event_callback(***,*invocation_context*,*event*)¶**
Log events yielded from the runner.


**Return type:**
Optional[[Event]


***async*on_model_error_callback(***,*callback_context*,*llm_request*,*error*)¶**
Log LLM error.


**Return type:**
Optional[LlmResponse]


***async*on_tool_error_callback(***,*tool*,*tool_args*,*tool_context*,*error*)¶**
Log tool error.


**Return type:**
Optional[dict]


***async*on_user_message_callback(***,*invocation_context*,*user_message*)¶**
Log user message and invocation start.


**Return type:**
Optional[Content]


***class*google.adk.plugins.PluginManager(*plugins**=**None*,*close_timeout**=**5.0*)¶**
Bases:object

Manages the registration and execution of plugins.

The PluginManager is an internal class that orchestrates the invocation of plugin callbacks at key points in the SDK’s execution lifecycle. It maintains a list of registered plugins and ensures they are called in the order they were registered.

The core execution logic implements an “early exit” strategy: if any plugin callback returns a non-Nonevalue, the execution of subsequent plugins for that specific event is halted, and the returned value is propagated up the call stack. This allows plugins to short-circuit operations like agent runs, tool calls, or model requests.

Initializes the plugin service.


**Parameters:**
**plugins**– An optional list of plugins to register upon initialization.

**close_timeout**– The timeout in seconds for each plugin’s close method.


***async*close()¶**
Calls the close method on all registered plugins concurrently.


**Return type:**
None


**Raises:**
**RuntimeError**– If one or more plugins failed to close, containing details of all failures.


**get_plugin(*plugin_name*)¶**
Retrieves a registered plugin by its name.


**Return type:**
Optional[[BasePlugin]


**Parameters:**
**plugin_name**– The name of the plugin to retrieve.


**Returns:**
The plugin instance if found; otherwise,None.


**register_plugin(*plugin*)¶**
Registers a new plugin.


**Return type:**
None


**Parameters:**
**plugin**– The plugin instance to register.


**Raises:**
**ValueError**– If a plugin with the same name is already registered.


***async*run_after_agent_callback(***,*agent*,*callback_context*)¶**
Runs theafter_agent_callbackfor all plugins.


**Return type:**
Optional[Content]


***async*run_after_model_callback(***,*callback_context*,*llm_response*)¶**
Runs theafter_model_callbackfor all plugins.


**Return type:**
Optional[LlmResponse]


***async*run_after_run_callback(***,*invocation_context*)¶**
Runs theafter_run_callbackfor all plugins.


**Return type:**
None


***async*run_after_tool_callback(***,*tool*,*tool_args*,*tool_context*,*result*)¶**
Runs theafter_tool_callbackfor all plugins.


**Return type:**
Optional[dict]


***async*run_before_agent_callback(***,*agent*,*callback_context*)¶**
Runs thebefore_agent_callbackfor all plugins.


**Return type:**
Optional[Content]


***async*run_before_model_callback(***,*callback_context*,*llm_request*)¶**
Runs thebefore_model_callbackfor all plugins.


**Return type:**
Optional[LlmResponse]


***async*run_before_run_callback(***,*invocation_context*)¶**
Runs thebefore_run_callbackfor all plugins.


**Return type:**
Optional[Content]


***async*run_before_tool_callback(***,*tool*,*tool_args*,*tool_context*)¶**
Runs thebefore_tool_callbackfor all plugins.


**Return type:**
Optional[dict]


***async*run_on_event_callback(***,*invocation_context*,*event*)¶**
Runs theon_event_callbackfor all plugins.


**Return type:**
Optional[[Event]


***async*run_on_model_error_callback(***,*callback_context*,*llm_request*,*error*)¶**
Runs theon_model_error_callbackfor all plugins.


**Return type:**
Optional[LlmResponse]


***async*run_on_tool_error_callback(***,*tool*,*tool_args*,*tool_context*,*error*)¶**
Runs theon_tool_error_callbackfor all plugins.


**Return type:**
Optional[dict]


***async*run_on_user_message_callback(***,*user_message*,*invocation_context*)¶**
Runs theon_user_message_callbackfor all plugins.


**Return type:**
Optional[Content]


***class*google.adk.plugins.ReflectAndRetryToolPlugin(*name**=**'reflect_retry_tool_plugin'*,*max_retries**=**3*,*throw_exception_if_retry_exceeded**=**True*,*tracking_scope**=**TrackingScope.INVOCATION*)¶**
Bases:[BasePlugin

Provides self-healing, concurrent-safe error recovery for tool failures.

This plugin intercepts tool failures, provides structured guidance to the LLM for reflection and correction, and retries the operation up to a configurable limit.

**Key Features:**

**Concurrency Safe:**Uses locking to safely handle parallel tool

executions -**Configurable Scope:**Tracks failures per-invocation (default) or globally

using theTrackingScopeenum.

**Extensible Scoping:**The_get_scope_keymethod can be overridden to implement custom tracking logic (e.g., per-user or per-session).

**Granular Tracking:**Failure counts are tracked per-tool within the defined scope. A success with one tool resets its counter without affecting others.

**Custom Error Extraction:**Supports detecting errors in normal tool

responses that

don’t throw exceptions, by overriding theextract_error_from_resultmethod.

**Example:**[``[`python from my_project.plugins import ReflectAndRetryToolPlugin, TrackingScope

# Example 1: (MOST COMMON USAGE): # Track failures only within the current agent invocation (default). error_handling_plugin = ReflectAndRetryToolPlugin(max_retries=3)

# Example 2: # Track failures globally across all turns and users. global_error_handling_plugin = ReflectAndRetryToolPlugin(max_retries=5, scope=TrackingScope.GLOBAL)

# Example 3: # Retry on failures but do not throw exceptions. error_handling_plugin =

ReflectAndRetryToolPlugin(max_retries=3, throw_exception_if_retry_exceeded=False)

# Example 4: # Track failures in successful tool responses that contain errors. class CustomRetryPlugin(ReflectAndRetryToolPlugin):

async def extract_error_from_result(self,[*, tool, tool_args,tool_context, result):

# Detect error based on response content if result.get(‘status’) == ‘error’:

return result

return None # No error detected

error_handling_plugin = CustomRetryPlugin(max_retries=5)[``[`

Initializes the ReflectAndRetryToolPlugin.


**Parameters:**
**name**– Plugin instance identifier.

**max_retries**– Maximum consecutive failures before giving up (0 = no retries).

**throw_exception_if_retry_exceeded**– If True, raises the final exception when the retry limit is reached. If False, returns guidance instead.

**tracking_scope**– Determines the lifecycle of the error tracking state. Defaults toTrackingScope.INVOCATIONtracking per-invocation.


***async*after_tool_callback(***,*tool*,*tool_args*,*tool_context*,*result*)¶**
Handles successful tool calls or extracts and processes errors.


**Return type:**
Optional[dict[str,Any]]


**Parameters:**
**tool**– The tool that was called.

**tool_args**– The arguments passed to the tool.

**tool_context**– The context of the tool call.

**result**– The result of the tool call.


**Returns:**
An optional dictionary containing reflection guidance if an error is detected, or None if the tool call was successful or the response is already a reflection message.


***async*extract_error_from_result(***,*tool*,*tool_args*,*tool_context*,*result*)¶**
Extracts an error from a successful tool result and triggers retry logic.

This is useful when tool call finishes successfully but the result contains an error object like {“error”: …} that should be handled by the plugin.

By overriding this method, you can trigger retry logic on these successful results that contain errors.


**Return type:**
Optional[dict[str,Any]]


**Parameters:**
**tool**– The tool that was called.

**tool_args**– The arguments passed to the tool.

**tool_context**– The context of the tool call.

**result**– The result of the tool call.


**Returns:**
The extracted error if any, or None if no error was detected.


***async*on_tool_error_callback(***,*tool*,*tool_args*,*tool_context*,*error*)¶**
Handles tool exceptions by providing reflection guidance.


**Return type:**
Optional[dict[str,Any]]


**Parameters:**
**tool**– The tool that was called.

**tool_args**– The arguments passed to the tool.

**tool_context**– The context of the tool call.

**error**– The exception raised by the tool.


**Returns:**
An optional dictionary containing reflection guidance for the error.