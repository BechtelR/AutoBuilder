# google.adk.runners module¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.runners

***class*google.adk.runners.InMemoryRunner(*agent**=**None*,***,*app_name**=**None*,*plugins**=**None*,*app**=**None*,*plugin_close_timeout**=**5.0*)¶**
Bases:[Runner

An in-memory Runner for testing and development.

This runner uses in-memory implementations for artifact, session, and memory services, providing a lightweight and self-contained environment for agent execution.


**agent¶**
The root agent to run.


**app_name¶**
The application name of the runner. Defaults to ‘InMemoryRunner’.

Initializes the InMemoryRunner.


**Parameters:**
**agent**– The root agent to run.

**app_name**– The application name of the runner. Defaults to ‘InMemoryRunner’.

**plugins**– Optional list of plugins for the runner.

**app**– Optional App instance.

**plugin_close_timeout**– The timeout in seconds for plugin close methods.


***class*google.adk.runners.Runner(***,*app**=**None*,*app_name**=**None*,*agent**=**None*,*plugins**=**None*,*artifact_service**=**None*,*session_service*,*memory_service**=**None*,*credential_service**=**None*,*plugin_close_timeout**=**5.0*,*auto_create_session**=**False*)¶**
Bases:object

The Runner class is used to run agents.

It manages the execution of an agent within a session, handling message processing, event generation, and interaction with various services like artifact storage, session management, and memory.


**app_name¶**
The application name of the runner.


**agent¶**
The root agent to run.


**artifact_service¶**
The artifact service for the runner.


**plugin_manager¶**
The plugin manager for the runner.


**session_service¶**
The session service for the runner.


**memory_service¶**
The memory service for the runner.


**credential_service¶**
The credential service for the runner.


**context_cache_config¶**
The context cache config for the runner.


**resumability_config¶**
The resumability config for the application.

Initializes the Runner.

Developers should provide either anappinstance or bothapp_nameandagent. Whenappis provided,app_namecan optionally override the app’s name (useful for deployment scenarios like Agent Engine where the resource name differs from the app’s identifier). However,agentshould not be provided whenappis provided. Providingappis the recommended way to create a runner.


**Parameters:**
**app**– An optionalAppinstance. If provided,agentshould not be specified.app_namecan optionally overrideapp.name.

**app_name**– The application name of the runner. Required ifappis not provided. Ifappis provided, this can optionally overrideapp.name(e.g., for deployment scenarios where a resource name differs from the app identifier).

**agent**– The root agent to run. Required ifappis not provided. Should not be provided whenappis provided.

**plugins**– Deprecated. A list of plugins for the runner. Please use theappargument to provide plugins instead.

**artifact_service**– The artifact service for the runner.

**session_service**– The session service for the runner.

**memory_service**– The memory service for the runner.

**credential_service**– The credential service for the runner.

**plugin_close_timeout**– The timeout in seconds for plugin close methods.

**auto_create_session**– Whether to automatically create a session when not found. Defaults to False. If False, a missing session raises ValueError with a helpful message.


**Raises:**
**ValueError**– Ifappis provided along withagentorplugins, or ifappis not provided but eitherapp_nameoragentis missing.


**Self*=**typing.Self*¶**

**agent*:*[*BaseAgent*¶**
The root agent to run.


**app_name*:**str*¶**
The app name of the runner.


**artifact_service*:*[*BaseArtifactService**|**None**=**None*¶**
The artifact service for the runner.


***async*close()¶**
Closes the runner.


**context_cache_config*:**ContextCacheConfig**|**None**=**None*¶**
The context cache config for the runner.


**credential_service*:**BaseCredentialService**|**None**=**None*¶**
The credential service for the runner.


**memory_service*:*[*BaseMemoryService**|**None**=**None*¶**
The memory service for the runner.


**plugin_manager*:*[*PluginManager*¶**
The plugin manager for the runner.


**resumability_config*:*[*ResumabilityConfig**|**None**=**None*¶**
The resumability config for the application.


***async*rewind_async(***,*user_id*,*session_id*,*rewind_before_invocation_id*)¶**
Rewinds the session to before the specified invocation.


**Return type:**
None


**run(***,*user_id*,*session_id*,*new_message*,*run_config**=**None*)¶**
Runs the agent.


**Return type:**
Generator[[Event,None,None]

Note

This sync interface is only for local testing and convenience purpose. Consider usingrun_asyncfor production usage.

If event compaction is enabled in the App configuration, it will be performed after all agent events for the current invocation have been yielded. The generator will only finish iterating after event compaction is complete.


**Parameters:**
**user_id**– The user ID of the session.

**session_id**– The session ID of the session.

**new_message**– A new message to append to the session.

**run_config**– The run config for the agent.


**Yields:**
The events generated by the agent.


***async*run_async(***,*user_id*,*session_id*,*invocation_id**=**None*,*new_message**=**None*,*state_delta**=**None*,*run_config**=**None*)¶**
Main entry method to run the agent in this runner.

If event compaction is enabled in the App configuration, it will be performed after all agent events for the current invocation have been yielded. The async generator will only finish iterating after event compaction is complete. However, this does not block newrun_asynccalls for subsequent user queries, which can be started concurrently.


**Return type:**
AsyncGenerator[[Event,None]


**Parameters:**
**user_id**– The user ID of the session.

**session_id**– The session ID of the session.

**invocation_id**– The invocation ID of the session, set this to resume an interrupted invocation.

**new_message**– A new message to append to the session.

**state_delta**– Optional state changes to apply to the session.

**run_config**– The run config for the agent.


**Yields:**
The events generated by the agent.


**Raises:**
**ValueError**– If the session is not found; If both invocation_id and new_message are None.


***async*run_debug(*user_messages*,***,*user_id**=**'debug_user_id'*,*session_id**=**'debug_session_id'*,*run_config**=**None*,*quiet**=**False*,*verbose**=**False*)¶**
Debug helper for quick agent experimentation and testing.

This convenience method is designed for developers getting started with ADK who want to quickly test agents without dealing with session management, content formatting, or event streaming. It automatically handles common boilerplate while hiding complexity.

IMPORTANT: This is for debugging and experimentation only. For production use, please use the standard run_async() method which provides full control over session management, event streaming, and error handling.


**Return type:**
list[[Event]


**Parameters:**
**user_messages**– Message(s) to send to the agent. Can be: - Single string: “What is 2+2?” - List of strings: [“Hello!”, “What’s my name?”]

**user_id**– User identifier. Defaults to “debug_user_id”.

**session_id**– Session identifier for conversation persistence. Defaults to “debug_session_id”. Reuse the same ID to continue a conversation.

**run_config**– Optional configuration for the agent execution.

**quiet**– If True, suppresses console output. Defaults to False (output shown).

**verbose**– If True, shows detailed tool calls and responses. Defaults to False for cleaner output showing only final agent responses.


**Returns:**
All events from all messages.


**Return type:**
list[[Event]


**Raises:**
**ValueError**– If session creation/retrieval fails.

Examples

Quick debugging: >>> runner = InMemoryRunner(agent=my_agent) >>> await runner.run_debug(“What is 2+2?”)

Multiple queries in conversation: >>> await runner.run_debug([“Hello!”, “What’s my name?”])

Continue a debug session: >>> await runner.run_debug(“What did we discuss?”) # Continues default session

Separate debug sessions: >>> await runner.run_debug(“Hi”, user_id=”alice”, session_id=”debug1”) >>> await runner.run_debug(“Hi”, user_id=”bob”, session_id=”debug2”)

Capture events for inspection: >>> events = await runner.run_debug(“Analyze this”) >>> for event in events: … inspect_event(event)

Note

For production applications requiring: - Custom session/memory services (Spanner, Cloud SQL, etc.) - Fine-grained event processing and streaming - Error recovery and resumability - Performance optimization Please use run_async() with proper configuration.


***async*run_live(***,*user_id**=**None*,*session_id**=**None*,*live_request_queue*,*run_config**=**None*,*session**=**None*)¶**
Runs the agent in live mode (experimental feature).

Therun_livemethod yields a stream ofEventobjects, but not all yielded events are saved to the session. Here’s a breakdown:


**Return type:**
AsyncGenerator[[Event,None]

**Events Yielded to Callers:*****Live Model Audio Events with Inline Data:**Events containing raw

audioBlobdata(inline_data).

**Live Model Audio Events with File Data:**Both input and ouput audio data are aggregated into an audio file saved into artifacts. The reference to the file is saved in the event asfile_data.

**Usage Metadata:**Events containing token usage.

**Transcription Events:**Both partial and non-partial transcription events are yielded.

**Function Call and Response Events:**Always saved.

**Other Control Events:**Most control events are saved.

**Events Saved to the Session:*****Live Model Audio Events with File Data:**Both input and ouput audio

data are aggregated into an audio file saved into artifacts. The reference to the file is saved as event in thefile_datato session if RunConfig.save_live_model_audio_to_session is True.

**Usage Metadata Events:**Saved to the session.

**Non-Partial Transcription Events:**Non-partial transcription events are saved.

**Function Call and Response Events:**Always saved.

**Other Control Events:**Most control events are saved.

**Events Not Saved to the Session:*****Live Model Audio Events with Inline Data:**Events containing raw

audioBlobdata are**not**saved to the session.


**Parameters:**
**user_id**– The user ID for the session. Required ifsessionis None.

**session_id**– The session ID for the session. Required ifsessionis None.

**live_request_queue**– The queue for live requests.

**run_config**– The run config for the agent.

**session**– The session to use. This parameter is deprecated, please useuser_idandsession_idinstead.


**Yields:**
*AsyncGenerator[Event, None]*– An asynchronous generator that yieldsEventobjects as they are produced by the agent during its live execution.

Warning

This feature is**experimental**and its API or behavior may change in future releases.

Note

Eithersessionor bothuser_idandsession_idmust be provided.


**session_service*:*[*BaseSessionService*¶**
The session service for the runner.

## AutoBuilder Errata

**`InMemoryRunner` does not expose `auto_create_session`:** The constructor doesn't pass this parameter to the parent `Runner`. Default is `False`, causing `ValueError: Session not found` when passing `session_id` to `run_async()`. Workaround: set `runner.auto_create_session = True` after construction. See `adk/ERRATA.md` #2.