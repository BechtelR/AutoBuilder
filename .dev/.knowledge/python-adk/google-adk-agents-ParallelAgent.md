Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.agents

***pydantic**model*google.adk.agents.ParallelAgent¶**
Bases:[BaseAgent

A shell agent that runs its sub-agents in parallel in an isolated manner.

This approach is beneficial for scenarios requiring multiple perspectives or attempts on a single task, such as:

Running different algorithms simultaneously.

Generating multiple responses for review by a subsequent evaluation agent.


```
Show JSON schema{
   "title": "ParallelAgent",
   "description": "A shell agent that runs its sub-agents in parallel in an isolated manner.\n\nThis approach is beneficial for scenarios requiring multiple perspectives or\nattempts on a single task, such as:\n\n- Running different algorithms simultaneously.\n- Generating multiple responses for review by a subsequent evaluation agent.",
   "type": "object",
   "properties": {
      "name": {
         "title": "Name",
         "type": "string"
      },
      "description": {
         "default": "",
         "title": "Description",
         "type": "string"
      },
      "parent_agent": {
         "anyOf": [
            {
               "$ref": "#/$defs/BaseAgent"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "sub_agents": {
         "items": {
            "$ref": "#/$defs/BaseAgent"
         },
         "title": "Sub Agents",
         "type": "array"
      },
      "before_agent_callback": {
         "default": null,
         "title": "Before Agent Callback",
         "type": "null"
      },
      "after_agent_callback": {
         "default": null,
         "title": "After Agent Callback",
         "type": "null"
      }
   },
   "$defs": {
      "BaseAgent": {
         "additionalProperties": false,
         "description": "Base class for all agents in Agent Development Kit.",
         "properties": {
            "name": {
               "title": "Name",
               "type": "string"
            },
            "description": {
               "default": "",
               "title": "Description",
               "type": "string"
            },
            "parent_agent": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/BaseAgent"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "sub_agents": {
               "items": {
                  "$ref": "#/$defs/BaseAgent"
               },
               "title": "Sub Agents",
               "type": "array"
            },
            "before_agent_callback": {
               "default": null,
               "title": "Before Agent Callback",
               "type": "null"
            },
            "after_agent_callback": {
               "default": null,
               "title": "After Agent Callback",
               "type": "null"
            }
         },
         "required": [
            "name"
         ],
         "title": "BaseAgent",
         "type": "object"
      }
   },
   "additionalProperties": false,
   "required": [
      "name"
   ]
}
```


**Fields:**

**Validators:**

**config_type¶**
alias ofParallelAgentConfig


***pydantic**model*google.adk.agents.RunConfig¶**
Bases:BaseModel

Configs for runtime behavior of agents.

The configs here will be overridden by agent-specific configurations.


```
Show JSON schema{
   "title": "RunConfig",
   "description": "Configs for runtime behavior of agents.\n\nThe configs here will be overridden by agent-specific configurations.",
   "type": "object",
   "properties": {
      "speech_config": {
         "anyOf": [
            {
               "$ref": "#/$defs/SpeechConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "response_modalities": {
         "anyOf": [
            {
               "items": {
                  "type": "string"
               },
               "type": "array"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Response Modalities"
      },
      "save_input_blobs_as_artifacts": {
         "default": false,
         "deprecated": true,
         "description": "Whether or not to save the input blobs as artifacts. DEPRECATED: Use SaveFilesAsArtifactsPlugin instead for better control and flexibility. See google.adk.plugins.SaveFilesAsArtifactsPlugin.",
         "title": "Save Input Blobs As Artifacts",
         "type": "boolean"
      },
      "support_cfc": {
         "default": false,
         "title": "Support Cfc",
         "type": "boolean"
      },
      "streaming_mode": {
         "$ref": "#/$defs/StreamingMode",
         "default": null
      },
      "output_audio_transcription": {
         "anyOf": [
            {
               "$ref": "#/$defs/AudioTranscriptionConfig"
            },
            {
               "type": "null"
            }
         ]
      },
      "input_audio_transcription": {
         "anyOf": [
            {
               "$ref": "#/$defs/AudioTranscriptionConfig"
            },
            {
               "type": "null"
            }
         ]
      },
      "realtime_input_config": {
         "anyOf": [
            {
               "$ref": "#/$defs/RealtimeInputConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "enable_affective_dialog": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Enable Affective Dialog"
      },
      "proactivity": {
         "anyOf": [
            {
               "$ref": "#/$defs/ProactivityConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "session_resumption": {
         "anyOf": [
            {
               "$ref": "#/$defs/SessionResumptionConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "context_window_compression": {
         "anyOf": [
            {
               "$ref": "#/$defs/ContextWindowCompressionConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "save_live_blob": {
         "default": false,
         "title": "Save Live Blob",
         "type": "boolean"
      },
      "tool_thread_pool_config": {
         "anyOf": [
            {
               "$ref": "#/$defs/ToolThreadPoolConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "save_live_audio": {
         "default": false,
         "deprecated": true,
         "description": "DEPRECATED: Use save_live_blob instead. If set to True, it saves live video and audio data to session and artifact service.",
         "title": "Save Live Audio",
         "type": "boolean"
      },
      "max_llm_calls": {
         "default": 500,
         "title": "Max Llm Calls",
         "type": "integer"
      },
      "custom_metadata": {
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
         "title": "Custom Metadata"
      }
   },
   "$defs": {
      "ActivityHandling": {
         "description": "The different ways of handling user activity.",
         "enum": [
            "ACTIVITY_HANDLING_UNSPECIFIED",
            "START_OF_ACTIVITY_INTERRUPTS",
            "NO_INTERRUPTION"
         ],
         "title": "ActivityHandling",
         "type": "string"
      },
      "AudioTranscriptionConfig": {
         "additionalProperties": false,
         "description": "The audio transcription configuration in Setup.",
         "properties": {},
         "title": "AudioTranscriptionConfig",
         "type": "object"
      },
      "AutomaticActivityDetection": {
         "additionalProperties": false,
         "description": "Configures automatic detection of activity.",
         "properties": {
            "disabled": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "If enabled, detected voice and text input count as activity. If disabled, the client must send activity signals.",
               "title": "Disabled"
            },
            "startOfSpeechSensitivity": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/StartSensitivity"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Determines how likely speech is to be detected."
            },
            "endOfSpeechSensitivity": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/EndSensitivity"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Determines how likely detected speech is ended."
            },
            "prefixPaddingMs": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The required duration of detected speech before start-of-speech is committed. The lower this value the more sensitive the start-of-speech detection is and the shorter speech can be recognized. However, this also increases the probability of false positives.",
               "title": "Prefixpaddingms"
            },
            "silenceDurationMs": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The required duration of detected non-speech (e.g. silence) before end-of-speech is committed. The larger this value, the longer speech gaps can be without interrupting the user's activity but this will increase the model's latency.",
               "title": "Silencedurationms"
            }
         },
         "title": "AutomaticActivityDetection",
         "type": "object"
      },
      "ContextWindowCompressionConfig": {
         "additionalProperties": false,
         "description": "Enables context window compression -- mechanism managing model context window so it does not exceed given length.",
         "properties": {
            "triggerTokens": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Number of tokens (before running turn) that triggers context window compression mechanism.",
               "title": "Triggertokens"
            },
            "slidingWindow": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/SlidingWindow"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Sliding window compression mechanism."
            }
         },
         "title": "ContextWindowCompressionConfig",
         "type": "object"
      },
      "EndSensitivity": {
         "description": "End of speech sensitivity.",
         "enum": [
            "END_SENSITIVITY_UNSPECIFIED",
            "END_SENSITIVITY_HIGH",
            "END_SENSITIVITY_LOW"
         ],
         "title": "EndSensitivity",
         "type": "string"
      },
      "MultiSpeakerVoiceConfig": {
         "additionalProperties": false,
         "description": "Configuration for a multi-speaker text-to-speech request.",
         "properties": {
            "speakerVoiceConfigs": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/SpeakerVoiceConfig"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. A list of configurations for the voices of the speakers. Exactly two speaker voice configurations must be provided.",
               "title": "Speakervoiceconfigs"
            }
         },
         "title": "MultiSpeakerVoiceConfig",
         "type": "object"
      },
      "PrebuiltVoiceConfig": {
         "additionalProperties": false,
         "description": "The configuration for the prebuilt speaker to use.",
         "properties": {
            "voiceName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The name of the preset voice to use.",
               "title": "Voicename"
            }
         },
         "title": "PrebuiltVoiceConfig",
         "type": "object"
      },
      "ProactivityConfig": {
         "additionalProperties": false,
         "description": "Config for proactivity features.",
         "properties": {
            "proactiveAudio": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "If enabled, the model can reject responding to the last prompt. For\n        example, this allows the model to ignore out of context speech or to stay\n        silent if the user did not make a request, yet.",
               "title": "Proactiveaudio"
            }
         },
         "title": "ProactivityConfig",
         "type": "object"
      },
      "RealtimeInputConfig": {
         "additionalProperties": false,
         "description": "Marks the end of user activity.\n\nThis can only be sent if automatic (i.e. server-side) activity detection is\ndisabled.",
         "properties": {
            "automaticActivityDetection": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/AutomaticActivityDetection"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "If not set, automatic activity detection is enabled by default. If automatic voice detection is disabled, the client must send activity signals."
            },
            "activityHandling": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ActivityHandling"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Defines what effect activity has."
            },
            "turnCoverage": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/TurnCoverage"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Defines which input is included in the user's turn."
            }
         },
         "title": "RealtimeInputConfig",
         "type": "object"
      },
      "ReplicatedVoiceConfig": {
         "additionalProperties": false,
         "description": "ReplicatedVoiceConfig is used to configure replicated voice.",
         "properties": {
            "mimeType": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The mime type of the replicated voice.\n      ",
               "title": "Mimetype"
            },
            "voiceSampleAudio": {
               "anyOf": [
                  {
                     "format": "base64url",
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The sample audio of the replicated voice.\n      ",
               "title": "Voicesampleaudio"
            }
         },
         "title": "ReplicatedVoiceConfig",
         "type": "object"
      },
      "SessionResumptionConfig": {
         "additionalProperties": false,
         "description": "Configuration of session resumption mechanism.\n\nIncluded in `LiveConnectConfig.session_resumption`. If included server\nwill send `LiveServerSessionResumptionUpdate` messages.",
         "properties": {
            "handle": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Session resumption handle of previous session (session to restore).\n\nIf not present new session will be started.",
               "title": "Handle"
            },
            "transparent": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "If set the server will send `last_consumed_client_message_index` in the `session_resumption_update` messages to allow for transparent reconnections.",
               "title": "Transparent"
            }
         },
         "title": "SessionResumptionConfig",
         "type": "object"
      },
      "SlidingWindow": {
         "additionalProperties": false,
         "description": "Context window will be truncated by keeping only suffix of it.\n\nContext window will always be cut at start of USER role turn. System\ninstructions and `BidiGenerateContentSetup.prefix_turns` will not be\nsubject to the sliding window mechanism, they will always stay at the\nbeginning of context window.",
         "properties": {
            "targetTokens": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Session reduction target -- how many tokens we should keep. Window shortening operation has some latency costs, so we should avoid running it on every turn. Should be < trigger_tokens. If not set, trigger_tokens/2 is assumed.",
               "title": "Targettokens"
            }
         },
         "title": "SlidingWindow",
         "type": "object"
      },
      "SpeakerVoiceConfig": {
         "additionalProperties": false,
         "description": "Configuration for a single speaker in a multi speaker setup.",
         "properties": {
            "speaker": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. The name of the speaker. This should be the same as the speaker name used in the prompt.",
               "title": "Speaker"
            },
            "voiceConfig": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/VoiceConfig"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. The configuration for the voice of this speaker."
            }
         },
         "title": "SpeakerVoiceConfig",
         "type": "object"
      },
      "SpeechConfig": {
         "additionalProperties": false,
         "properties": {
            "voiceConfig": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/VoiceConfig"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Configuration for the voice of the response."
            },
            "languageCode": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Language code (ISO 639. e.g. en-US) for the speech synthesization.",
               "title": "Languagecode"
            },
            "multiSpeakerVoiceConfig": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/MultiSpeakerVoiceConfig"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The configuration for a multi-speaker text-to-speech request. This field is mutually exclusive with `voice_config`."
            }
         },
         "title": "SpeechConfig",
         "type": "object"
      },
      "StartSensitivity": {
         "description": "Start of speech sensitivity.",
         "enum": [
            "START_SENSITIVITY_UNSPECIFIED",
            "START_SENSITIVITY_HIGH",
            "START_SENSITIVITY_LOW"
         ],
         "title": "StartSensitivity",
         "type": "string"
      },
      "StreamingMode": {
         "description": "Streaming modes for agent execution.\n\nThis enum defines different streaming behaviors for how the agent returns\nevents as model response.",
         "enum": [
            null,
            "sse",
            "bidi"
         ],
         "title": "StreamingMode"
      },
      "ToolThreadPoolConfig": {
         "additionalProperties": false,
         "description": "Configuration for the tool thread pool executor.\n\nAttributes:\n  max_workers: Maximum number of worker threads in the pool. Defaults to 4.",
         "properties": {
            "max_workers": {
               "default": 4,
               "description": "Maximum number of worker threads in the pool.",
               "minimum": 1,
               "title": "Max Workers",
               "type": "integer"
            }
         },
         "title": "ToolThreadPoolConfig",
         "type": "object"
      },
      "TurnCoverage": {
         "description": "Options about which input is included in the user's turn.",
         "enum": [
            "TURN_COVERAGE_UNSPECIFIED",
            "TURN_INCLUDES_ONLY_ACTIVITY",
            "TURN_INCLUDES_ALL_INPUT"
         ],
         "title": "TurnCoverage",
         "type": "string"
      },
      "VoiceConfig": {
         "additionalProperties": false,
         "properties": {
            "replicatedVoiceConfig": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ReplicatedVoiceConfig"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "If true, the model will use a replicated voice for the response."
            },
            "prebuiltVoiceConfig": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/PrebuiltVoiceConfig"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The configuration for the prebuilt voice to use."
            }
         },
         "title": "VoiceConfig",
         "type": "object"
      }
   },
   "additionalProperties": false
}
```


**Fields:**
context_window_compression (google.genai.types.ContextWindowCompressionConfig | None)

custom_metadata (dict[str, Any] | None)

enable_affective_dialog (bool | None)

input_audio_transcription (google.genai.types.AudioTranscriptionConfig | None)

max_llm_calls (int)

output_audio_transcription (google.genai.types.AudioTranscriptionConfig | None)

proactivity (google.genai.types.ProactivityConfig | None)

realtime_input_config (google.genai.types.RealtimeInputConfig | None)

response_modalities (list[str] | None)

save_input_blobs_as_artifacts (bool)

save_live_audio (bool)

save_live_blob (bool)

session_resumption (google.genai.types.SessionResumptionConfig | None)

speech_config (google.genai.types.SpeechConfig | None)

streaming_mode (google.adk.agents.run_config.StreamingMode)

support_cfc (bool)

tool_thread_pool_config (google.adk.agents.run_config.ToolThreadPoolConfig | None)


**Validators:**
check_for_deprecated_save_live_audio»all fields

validate_max_llm_calls»max_llm_calls


***field*context_window_compression*:**types.ContextWindowCompressionConfig**|**None**=**None*¶**
Configuration for context window compression. If set, this will enable context window compression for LLM input.


**Validated by:**
check_for_deprecated_save_live_audio


***field*custom_metadata*:**dict**[**str**,**Any**]**|**None**=**None*¶**
Custom metadata for the current invocation.


**Validated by:**
check_for_deprecated_save_live_audio


***field*enable_affective_dialog*:**bool**|**None**=**None*¶**
If enabled, the model will detect emotions and adapt its responses accordingly.


**Validated by:**
check_for_deprecated_save_live_audio


***field*input_audio_transcription*:**types.AudioTranscriptionConfig**|**None**[Optional]*¶**
Input transcription for live agents with audio input from user.


**Validated by:**
check_for_deprecated_save_live_audio


***field*max_llm_calls*:**int**=**500*¶**
A limit on the total number of llm calls for a given run.


**Valid Values:**
More than 0 and less than sys.maxsize: The bound on the number of llm calls is enforced, if the value is set in this range.

Less than or equal to 0: This allows for unbounded number of llm calls.


**Validated by:**
check_for_deprecated_save_live_audio

validate_max_llm_calls


***field*output_audio_transcription*:**types.AudioTranscriptionConfig**|**None**[Optional]*¶**
Output transcription for live agents with audio response.


**Validated by:**
check_for_deprecated_save_live_audio


***field*proactivity*:**types.ProactivityConfig**|**None**=**None*¶**
Configures the proactivity of the model. This allows the model to respond proactively to the input and to ignore irrelevant input.


**Validated by:**
check_for_deprecated_save_live_audio


***field*realtime_input_config*:**types.RealtimeInputConfig**|**None**=**None*¶**
Realtime input config for live agents with audio input from user.


**Validated by:**
check_for_deprecated_save_live_audio


***field*response_modalities*:**list**[**str**]**|**None**=**None*¶**
The output modalities. If not set, it’s default to AUDIO.


**Validated by:**
check_for_deprecated_save_live_audio


***field*save_live_blob*:**bool**=**False*¶**
Saves live video and audio data to session and artifact service.


**Validated by:**
check_for_deprecated_save_live_audio


***field*session_resumption*:**types.SessionResumptionConfig**|**None**=**None*¶**
Configures session resumption mechanism. Only support transparent session resumption mode now.


**Validated by:**
check_for_deprecated_save_live_audio


***field*speech_config*:**types.SpeechConfig**|**None**=**None*¶**
Speech configuration for the live agent.


**Validated by:**
check_for_deprecated_save_live_audio


***field*streaming_mode*:**StreamingMode**=**StreamingMode.NONE*¶**
Streaming mode, None or StreamingMode.SSE or StreamingMode.BIDI.


**Validated by:**
check_for_deprecated_save_live_audio


***field*support_cfc*:**bool**=**False*¶**
Whether to support CFC (Compositional Function Calling). Only applicable for StreamingMode.SSE. If it’s true. the LIVE API will be invoked. Since only LIVE API supports CFC

Warning

This feature is**experimental**and its API or behavior may change in future releases.


**Validated by:**
check_for_deprecated_save_live_audio


***field*tool_thread_pool_config*:**ToolThreadPoolConfig**|**None**=**None*¶**
Configuration for running tools in a thread pool for live mode.

When set, tool executions will run in a separate thread pool executor instead of the main event loop. When None (default), tools run in the main event loop.

This helps keep the event loop responsive for: - User interruptions to be processed immediately - Model responses to continue being received

Both sync and async tools are supported. Async tools are run in a new event loop within the background thread, which helps catch blocking I/O mistakenly used inside async functions.

IMPORTANT - GIL (Global Interpreter Lock) Considerations:

Thread pool HELPS with (GIL is released): - Blocking I/O: time.sleep(), network calls, file I/O, database queries - C extensions: numpy, hashlib, image processing libraries - Async functions containing blocking I/O (common user mistake)

Thread pool does NOT help with (GIL is held): - Pure Python CPU-bound code: loops, calculations, recursive algorithms - The GIL prevents true parallel execution for Python bytecode

For CPU-intensive Python code, consider alternatives: - Use C extensions that release the GIL - Break work into chunks with periodicawait asyncio.sleep(0)- Use multiprocessing (ProcessPoolExecutor) for true parallelism

Example

[``[`python from google.adk.agents.run_config import RunConfig, ToolThreadPoolConfig

# Enable thread pool with default settings run_config = RunConfig(

tool_thread_pool_config=ToolThreadPoolConfig(),

)

# Enable thread pool with custom max_workers run_config = RunConfig(

tool_thread_pool_config=ToolThreadPoolConfig(max_workers=8),


## )¶

**Validated by:**
check_for_deprecated_save_live_audio


***validator*check_for_deprecated_save_live_audio*»**all**fields*¶**
If save_live_audio is passed, use it to set save_live_blob.


**Return type:**
Any


***validator*validate_max_llm_calls*»**max_llm_calls*¶**

**Return type:**
int


**save_input_blobs_as_artifacts*:**bool*¶**
Read-only data descriptor used to emit a runtime deprecation warning before accessing a deprecated field.


**msg¶**
The deprecation message to be emitted.


**wrapped_property¶**
The property instance if the deprecated field is a computed field, orNone.


**field_name¶**
The name of the field being deprecated.


**save_live_audio*:**bool*¶**
Read-only data descriptor used to emit a runtime deprecation warning before accessing a deprecated field.


**msg¶**
The deprecation message to be emitted.


**wrapped_property¶**
The property instance if the deprecated field is a computed field, orNone.


**field_name¶**
The name of the field being deprecated.