# google.adk.models module¶
Defines the interface to support a model.


***pydantic**model*google.adk.models.BaseLlm¶**
Bases:BaseModel

The BaseLLM class.


```
Show JSON schema{
   "title": "BaseLlm",
   "description": "The BaseLLM class.",
   "type": "object",
   "properties": {
      "model": {
         "title": "Model",
         "type": "string"
      }
   },
   "required": [
      "model"
   ]
}
```


**Fields:**
model (str)


***field*model*:**str**[Required]*¶**
The name of the LLM, e.g. gemini-2.5-flash or gemini-2.5-pro.


***classmethod*supported_models()¶**
Returns a list of supported models in regex for LlmRegistry.


**Return type:**
list[str]


**connect(*llm_request*)¶**
Creates a live connection to the LLM.


**Return type:**
BaseLlmConnection


**Parameters:**
**llm_request**– LlmRequest, the request to send to the LLM.


**Returns:**
BaseLlmConnection, the connection to the LLM.


***abstractmethod**async*generate_content_async(*llm_request*,*stream**=**False*)¶**
Generates content for a single model turn.

This method handles Server-Sent Events (SSE) streaming for unidirectional content generation. For bidirectional streaming (e.g., Gemini Live API), use theconnect()method instead.


**Args:**
llm_request: LlmRequest, the request to send to the LLM. stream: bool = False, whether to enable SSE streaming mode.


**Yields:**
LlmResponse objects representing the model’s response for one turn.

**Non-streaming mode (stream=False):**

Yields exactly one LlmResponse containing the complete model output (text, function calls, bytes, etc.). This response haspartial=False.

**Streaming mode (stream=True):**

Yields multiple LlmResponse objects as chunks arrive:

Intermediate chunks:partial=True(progressive updates)

Final chunk:partial=False(aggregated content from entire turn, identical to stream=False output)

Text consolidation: Consecutive text parts of the same type (thought/non-thought) SHOULD merge without separator, but client code must not rely on this - unconsolidated parts are unusual but also valid

**Common content in partial chunks:**

All intermediate chunks havepartial=Trueregardless of content type. Common examples include:

Text: Streams incrementally as tokens arrive

Function calls: May arrive in separate chunks

Bytes (e.g., images): Typically arrive as single chunk, interleaved with text

Thoughts: Stream incrementally when thinking_config is enabled

**Examples:**

Simple text streaming:


```
LlmResponse(partial=True,  parts=["The weather"])
LlmResponse(partial=True,  parts=[" in Tokyo is"])
LlmResponse(partial=True,  parts=[" sunny."])
LlmResponse(partial=False, parts=["The weather in Tokyo is sunny."])
```

Text + function call:


```
LlmResponse(partial=True,  parts=[Text("Let me check...")])
LlmResponse(partial=True,  parts=[FunctionCall("get_weather", ...)])
LlmResponse(partial=False, parts=[Text("Let me check..."),
                                  FunctionCall("get_weather", ...)])
```

Parallel function calls across chunks:


```
LlmResponse(partial=True,  parts=[Text("Checking both cities...")])
LlmResponse(partial=True,  parts=[FunctionCall("get_weather", Tokyo)])
LlmResponse(partial=True,  parts=[FunctionCall("get_weather", NYC)])
LlmResponse(partial=False, parts=[Text("Checking both cities..."),
                                  FunctionCall("get_weather", Tokyo),
                                  FunctionCall("get_weather", NYC)])
```

Text + bytes (image generation with gemini-2.5-flash-image):


```
LlmResponse(partial=True,  parts=[Text("Here's an image of a dog.")])
LlmResponse(partial=True,  parts=[Text("
```


**“)])**
LlmResponse(partial=True, parts=[Blob(image/png, 1.6MB)]) LlmResponse(partial=True, parts=[Text(“It carries a bone”)]) LlmResponse(partial=True, parts=[Text(” and running around.”)]) LlmResponse(partial=False, parts=[Text(“Here’s an image of a dog.


**“),**
Blob(image/png, 1.6MB), Text(“It carries a bone and running around.”)])

Note: Consecutive text parts before and after blob merge separately.

Text with thinking (gemini-2.5-flash with thinking_config):


```
LlmResponse(partial=True,  parts=[Thought("Let me analyze...")])
LlmResponse(partial=True,  parts=[Thought("The user wants...")])
LlmResponse(partial=True,  parts=[Text("Based on my analysis,")])
LlmResponse(partial=True,  parts=[Text(" the answer is 42.")])
LlmResponse(partial=False, parts=[Thought("Let me analyze...The user wants..."),
                                  Text("Based on my analysis, the answer is 42.")])
```

Note: Consecutive parts of same type merge (thoughts→thought, text→text).

**Important:**All yielded responses represent one logical model turn. The final response withpartial=Falseshould be identical to the response that would be received withstream=False.


**Return type:**
AsyncGenerator[LlmResponse,None]


***pydantic**model*google.adk.models.Gemini¶**
Bases:[BaseLlm

Integration for Gemini models.


**model¶**
The name of the Gemini model.


**use_interactions_api¶**
Whether to use the interactions API for model invocation.


```
Show JSON schema{
   "title": "Gemini",
   "description": "Integration for Gemini models.\n\nAttributes:\n  model: The name of the Gemini model.\n  use_interactions_api: Whether to use the interactions API for model\n    invocation.",
   "type": "object",
   "properties": {
      "model": {
         "default": "gemini-2.5-flash",
         "title": "Model",
         "type": "string"
      },
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
      "use_interactions_api": {
         "default": false,
         "title": "Use Interactions Api",
         "type": "boolean"
      },
      "retry_options": {
         "anyOf": [
            {
               "$ref": "#/$defs/HttpRetryOptions"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      }
   },
   "$defs": {
      "HttpRetryOptions": {
         "additionalProperties": false,
         "description": "HTTP retry options to be used in each of the requests.",
         "properties": {
            "attempts": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Maximum number of attempts, including the original request.\n      If 0 or 1, it means no retries. If not specified, default to 5.",
               "title": "Attempts"
            },
            "initialDelay": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Initial delay before the first retry, in fractions of a second. If not specified, default to 1.0 second.",
               "title": "Initialdelay"
            },
            "maxDelay": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Maximum delay between retries, in fractions of a second. If not specified, default to 60.0 seconds.",
               "title": "Maxdelay"
            },
            "expBase": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Multiplier by which the delay increases after each attempt. If not specified, default to 2.0.",
               "title": "Expbase"
            },
            "jitter": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Randomness factor for the delay. If not specified, default to 1.0.",
               "title": "Jitter"
            },
            "httpStatusCodes": {
               "anyOf": [
                  {
                     "items": {
                        "type": "integer"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "List of HTTP status codes that should trigger a retry.\n      If not specified, a default set of retryable codes (408, 429, and 5xx) may be used.",
               "title": "Httpstatuscodes"
            }
         },
         "title": "HttpRetryOptions",
         "type": "object"
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
   }
}
```


**Fields:**
model (str)

retry_options (Optional[types.HttpRetryOptions])

speech_config (Optional[types.SpeechConfig])

use_interactions_api (bool)


***field*model*:**str**=**'gemini-2.5-flash'*¶**
The name of the LLM, e.g. gemini-2.5-flash or gemini-2.5-pro.


***field*retry_options*:**types.HttpRetryOptions**|**None**=**None*¶**
Allow Gemini to retry failed responses.

Sample:[``[`python from google.genai import types

# …


**agent = Agent(**

**model=Gemini(**
retry_options=types.HttpRetryOptions(initial_delay=1, attempts=2),

)


## )¶

***field*speech_config*:**types.SpeechConfig**|**None**=**None*¶**

***field*use_interactions_api*:**bool**=**False*¶**
Whether to use the interactions API for model invocation.

When enabled, uses the interactions API (client.aio.interactions.create()) instead of the traditional generate_content API. The interactions API provides stateful conversation capabilities, allowing you to chain interactions using previous_interaction_id instead of sending full history. The response format will be converted to match the existing LlmResponse structure for compatibility.

Sample:[``[`python agent = Agent(

model=Gemini(use_interactions_api=True)


## )¶

***classmethod*supported_models()¶**
Provides the list of supported models.


**Return type:**
list[str]


**Returns:**
A list of supported models.


**connect(*llm_request*)¶**
Connects to the Gemini model and returns an llm connection.


**Return type:**
BaseLlmConnection


**Parameters:**
**llm_request**– LlmRequest, the request to send to the Gemini model.


**Yields:**
BaseLlmConnection, the connection to the Gemini model.


***async*generate_content_async(*llm_request*,*stream**=**False*)¶**
Sends a request to the Gemini model.


**Return type:**
AsyncGenerator[LlmResponse,None]


**Parameters:**
**llm_request**– LlmRequest, the request to send to the Gemini model.

**stream**– bool = False, whether to do streaming call.


**Yields:**
*LlmResponse*– The model response.


***property*api_client*:**Client*¶**
Provides the api client.


**Returns:**
The api client.


***pydantic**model*google.adk.models.Gemma¶**
Bases:GemmaFunctionCallingMixin,[Gemini

Integration for Gemma models exposed via the Gemini API.

Only Gemma 3 models are supported at this time. For agentic use cases, use of gemma-3-27b-it and gemma-3-12b-it are strongly recommended.

For full documentation, see:[https://ai.google.dev/gemma/docs/core/

NOTE: Gemma does**NOT**support system instructions. Any system instructions will be replaced with an initial*user*prompt in the LLM request. If system instructions change over the course of agent execution, the initial content**SHOULD**be replaced. Special care is warranted here. See:[https://ai.google.dev/gemma/docs/core/prompt-structure#system-instructions

NOTE: Gemma’s function calling support is limited. It does not have full access to the same built-in tools as Gemini. It also does not have special API support for tools and functions. Rather, tools must be passed in via auserprompt, and extracted from model responses based on approximate shape.

NOTE: Vertex AI API support for Gemma is not currently included. This**ONLY**supports usage via the Gemini API.


```
Show JSON schema{
   "title": "Gemma",
   "description": "Integration for Gemma models exposed via the Gemini API.\n\nOnly Gemma 3 models are supported at this time. For agentic use cases,\nuse of gemma-3-27b-it and gemma-3-12b-it are strongly recommended.\n\nFor full documentation, see: https://ai.google.dev/gemma/docs/core/\n\nNOTE: Gemma does **NOT** support system instructions. Any system instructions\nwill be replaced with an initial *user* prompt in the LLM request. If system\ninstructions change over the course of agent execution, the initial content\n**SHOULD** be replaced. Special care is warranted here.\nSee:\nhttps://ai.google.dev/gemma/docs/core/prompt-structure#system-instructions\n\nNOTE: Gemma's function calling support is limited. It does not have full\naccess to the\nsame built-in tools as Gemini. It also does not have special API support for\ntools and\nfunctions. Rather, tools must be passed in via a `user` prompt, and extracted\nfrom model\nresponses based on approximate shape.\n\nNOTE: Vertex AI API support for Gemma is not currently included. This **ONLY**\nsupports\nusage via the Gemini API.",
   "type": "object",
   "properties": {
      "model": {
         "default": "gemma-3-27b-it",
         "title": "Model",
         "type": "string"
      },
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
      "use_interactions_api": {
         "default": false,
         "title": "Use Interactions Api",
         "type": "boolean"
      },
      "retry_options": {
         "anyOf": [
            {
               "$ref": "#/$defs/HttpRetryOptions"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      }
   },
   "$defs": {
      "HttpRetryOptions": {
         "additionalProperties": false,
         "description": "HTTP retry options to be used in each of the requests.",
         "properties": {
            "attempts": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Maximum number of attempts, including the original request.\n      If 0 or 1, it means no retries. If not specified, default to 5.",
               "title": "Attempts"
            },
            "initialDelay": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Initial delay before the first retry, in fractions of a second. If not specified, default to 1.0 second.",
               "title": "Initialdelay"
            },
            "maxDelay": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Maximum delay between retries, in fractions of a second. If not specified, default to 60.0 seconds.",
               "title": "Maxdelay"
            },
            "expBase": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Multiplier by which the delay increases after each attempt. If not specified, default to 2.0.",
               "title": "Expbase"
            },
            "jitter": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Randomness factor for the delay. If not specified, default to 1.0.",
               "title": "Jitter"
            },
            "httpStatusCodes": {
               "anyOf": [
                  {
                     "items": {
                        "type": "integer"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "List of HTTP status codes that should trigger a retry.\n      If not specified, a default set of retryable codes (408, 429, and 5xx) may be used.",
               "title": "Httpstatuscodes"
            }
         },
         "title": "HttpRetryOptions",
         "type": "object"
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
   }
}
```


**Fields:**
model (str)


***field*model*:**str**=**'gemma-3-27b-it'*¶**
The name of the LLM, e.g. gemini-2.5-flash or gemini-2.5-pro.


***classmethod*supported_models()¶**
Provides the list of supported models.

Returns: A list of supported models.


**Return type:**
list[str]


***async*generate_content_async(*llm_request*,*stream**=**False*)¶**
Sends a request to the Gemma model.


**Return type:**
AsyncGenerator[LlmResponse,None]


**Parameters:**
**llm_request**– LlmRequest, the request to send to the Gemini model.

**stream**– bool = False, whether to do streaming call.


**Yields:**
*LlmResponse*– The model response.


***class*google.adk.models.LLMRegistry¶**
Bases:object

Registry for LLMs.


***static*new_llm(*model*)¶**
Creates a new LLM instance.


**Return type:**
[BaseLlm


**Parameters:**
**model**– The model name.


**Returns:**
The LLM instance.


***static*register(*llm_cls*)¶**
Registers a new LLM class.


**Parameters:**
**llm_cls**– The class that implements the model.


***static*resolve(*model*)¶**
Resolves the model to a BaseLlm subclass.


**Return type:**
type[[BaseLlm]


**Parameters:**
**model**– The model name.


**Returns:**
The BaseLlm subclass.


**Raises:**
**ValueError**– If the model is not found.


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