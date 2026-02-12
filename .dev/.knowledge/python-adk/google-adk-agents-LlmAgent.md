Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.agents

***pydantic**model*google.adk.agents.LlmAgent¶**
Bases:[BaseAgent

LLM-based Agent.


```
Show JSON schema{
   "title": "LlmAgent",
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
      },
      "model": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "$ref": "#/$defs/BaseLlm"
            }
         ],
         "default": "",
         "title": "Model"
      },
      "instruction": {
         "default": "",
         "title": "Instruction",
         "type": "string"
      },
      "global_instruction": {
         "default": "",
         "title": "Global Instruction",
         "type": "string"
      },
      "static_instruction": {
         "anyOf": [
            {
               "$ref": "#/$defs/Content"
            },
            {
               "type": "string"
            },
            {
               "$ref": "#/$defs/File"
            },
            {
               "$ref": "#/$defs/Part"
            },
            {
               "items": {
                  "anyOf": [
                     {
                        "type": "string"
                     },
                     {
                        "$ref": "#/$defs/File"
                     },
                     {
                        "$ref": "#/$defs/Part"
                     }
                  ]
               },
               "type": "array"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Static Instruction"
      },
      "tools": {
         "items": {
            "anyOf": []
         },
         "title": "Tools",
         "type": "array"
      },
      "generate_content_config": {
         "default": null,
         "title": "Generate Content Config"
      },
      "disallow_transfer_to_parent": {
         "default": false,
         "title": "Disallow Transfer To Parent",
         "type": "boolean"
      },
      "disallow_transfer_to_peers": {
         "default": false,
         "title": "Disallow Transfer To Peers",
         "type": "boolean"
      },
      "include_contents": {
         "default": "default",
         "enum": [
            "default",
            "none"
         ],
         "title": "Include Contents",
         "type": "string"
      },
      "input_schema": {
         "anyOf": [
            {},
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Input Schema"
      },
      "output_schema": {
         "anyOf": [
            {},
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Output Schema"
      },
      "output_key": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Output Key"
      },
      "planner": {
         "default": null,
         "title": "Planner"
      },
      "code_executor": {
         "anyOf": [
            {
               "$ref": "#/$defs/BaseCodeExecutor"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "before_model_callback": {
         "default": null,
         "title": "Before Model Callback",
         "type": "null"
      },
      "after_model_callback": {
         "default": null,
         "title": "After Model Callback",
         "type": "null"
      },
      "on_model_error_callback": {
         "default": null,
         "title": "On Model Error Callback",
         "type": "null"
      },
      "before_tool_callback": {
         "default": null,
         "title": "Before Tool Callback",
         "type": "null"
      },
      "after_tool_callback": {
         "default": null,
         "title": "After Tool Callback",
         "type": "null"
      },
      "on_tool_error_callback": {
         "default": null,
         "title": "On Tool Error Callback",
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
      },
      "BaseCodeExecutor": {
         "description": "Abstract base class for all code executors.\n\nThe code executor allows the agent to execute code blocks from model responses\nand incorporate the execution results into the final response.\n\nAttributes:\n  optimize_data_file: If true, extract and process data files from the model\n    request and attach them to the code executor. Supported data file\n    MimeTypes are [text/csv]. Default to False.\n  stateful: Whether the code executor is stateful. Default to False.\n  error_retry_attempts: The number of attempts to retry on consecutive code\n    execution errors. Default to 2.\n  code_block_delimiters: The list of the enclosing delimiters to identify the\n    code blocks.\n  execution_result_delimiters: The delimiters to format the code execution\n    result.",
         "properties": {
            "optimize_data_file": {
               "default": false,
               "title": "Optimize Data File",
               "type": "boolean"
            },
            "stateful": {
               "default": false,
               "title": "Stateful",
               "type": "boolean"
            },
            "error_retry_attempts": {
               "default": 2,
               "title": "Error Retry Attempts",
               "type": "integer"
            },
            "code_block_delimiters": {
               "default": [
                  [
                     "```tool_code\n",
                     "\n```"
                  ],
                  [
                     "```python\n",
                     "\n```"
                  ]
               ],
               "items": {
                  "maxItems": 2,
                  "minItems": 2,
                  "prefixItems": [
                     {
                        "type": "string"
                     },
                     {
                        "type": "string"
                     }
                  ],
                  "type": "array"
               },
               "title": "Code Block Delimiters",
               "type": "array"
            },
            "execution_result_delimiters": {
               "default": [
                  "```tool_output\n",
                  "\n```"
               ],
               "maxItems": 2,
               "minItems": 2,
               "prefixItems": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "string"
                  }
               ],
               "title": "Execution Result Delimiters",
               "type": "array"
            }
         },
         "title": "BaseCodeExecutor",
         "type": "object"
      },
      "BaseLlm": {
         "description": "The BaseLLM class.",
         "properties": {
            "model": {
               "title": "Model",
               "type": "string"
            }
         },
         "required": [
            "model"
         ],
         "title": "BaseLlm",
         "type": "object"
      },
      "Blob": {
         "additionalProperties": false,
         "description": "Content blob.",
         "properties": {
            "data": {
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
               "description": "Required. Raw bytes.",
               "title": "Data"
            },
            "displayName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Display name of the blob. Used to provide a label or filename to distinguish blobs. This field is only returned in PromptMessage for prompt management. It is currently used in the Gemini GenerateContent calls only when server side tools (code_execution, google_search, and url_context) are enabled. This field is not supported in Gemini API.",
               "title": "Displayname"
            },
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
               "description": "Required. The IANA standard MIME type of the source data.",
               "title": "Mimetype"
            }
         },
         "title": "Blob",
         "type": "object"
      },
      "CodeExecutionResult": {
         "additionalProperties": false,
         "description": "Result of executing the [ExecutableCode].\n\nOnly generated when using the [CodeExecution] tool, and always follows a\n`part` containing the [ExecutableCode].",
         "properties": {
            "outcome": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/Outcome"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. Outcome of the code execution."
            },
            "output": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Contains stdout when code execution is successful, stderr or other description otherwise.",
               "title": "Output"
            }
         },
         "title": "CodeExecutionResult",
         "type": "object"
      },
      "Content": {
         "additionalProperties": false,
         "description": "Contains the multi-part content of a message.",
         "properties": {
            "parts": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/Part"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "List of parts that constitute a single message. Each part may have\n      a different IANA MIME type.",
               "title": "Parts"
            },
            "role": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The producer of the content. Must be either 'user' or 'model'. Useful to set for multi-turn conversations, otherwise can be left blank or unset.",
               "title": "Role"
            }
         },
         "title": "Content",
         "type": "object"
      },
      "ExecutableCode": {
         "additionalProperties": false,
         "description": "Code generated by the model that is meant to be executed, and the result returned to the model.\n\nGenerated when using the [CodeExecution] tool, in which the code will be\nautomatically executed, and a corresponding [CodeExecutionResult] will also be\ngenerated.",
         "properties": {
            "code": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. The code to be executed.",
               "title": "Code"
            },
            "language": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/Language"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. Programming language of the `code`."
            }
         },
         "title": "ExecutableCode",
         "type": "object"
      },
      "File": {
         "additionalProperties": false,
         "description": "A file uploaded to the API.",
         "properties": {
            "name": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The `File` resource name. The ID (name excluding the \"files/\" prefix) can contain up to 40 characters that are lowercase alphanumeric or dashes (-). The ID cannot start or end with a dash. If the name is empty on create, a unique name will be generated. Example: `files/123-456`",
               "title": "Name"
            },
            "displayName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The human-readable display name for the `File`. The display name must be no more than 512 characters in length, including spaces. Example: 'Welcome Image'",
               "title": "Displayname"
            },
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
               "description": "Output only. MIME type of the file.",
               "title": "Mimetype"
            },
            "sizeBytes": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Size of the file in bytes.",
               "title": "Sizebytes"
            },
            "createTime": {
               "anyOf": [
                  {
                     "format": "date-time",
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The timestamp of when the `File` was created.",
               "title": "Createtime"
            },
            "expirationTime": {
               "anyOf": [
                  {
                     "format": "date-time",
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The timestamp of when the `File` will be deleted. Only set if the `File` is scheduled to expire.",
               "title": "Expirationtime"
            },
            "updateTime": {
               "anyOf": [
                  {
                     "format": "date-time",
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The timestamp of when the `File` was last updated.",
               "title": "Updatetime"
            },
            "sha256Hash": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. SHA-256 hash of the uploaded bytes. The hash value is encoded in base64 format.",
               "title": "Sha256Hash"
            },
            "uri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The URI of the `File`.",
               "title": "Uri"
            },
            "downloadUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The URI of the `File`, only set for downloadable (generated) files.",
               "title": "Downloaduri"
            },
            "state": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FileState"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Processing state of the File."
            },
            "source": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FileSource"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The source of the `File`."
            },
            "videoMetadata": {
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
               "description": "Output only. Metadata for a video.",
               "title": "Videometadata"
            },
            "error": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FileStatus"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Error status if File processing failed."
            }
         },
         "title": "File",
         "type": "object"
      },
      "FileData": {
         "additionalProperties": false,
         "description": "URI based data.",
         "properties": {
            "displayName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Display name of the file data. Used to provide a label or filename to distinguish file datas. This field is only returned in PromptMessage for prompt management. It is currently used in the Gemini GenerateContent calls only when server side tools (code_execution, google_search, and url_context) are enabled. This field is not supported in Gemini API.",
               "title": "Displayname"
            },
            "fileUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. URI.",
               "title": "Fileuri"
            },
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
               "description": "Required. The IANA standard MIME type of the source data.",
               "title": "Mimetype"
            }
         },
         "title": "FileData",
         "type": "object"
      },
      "FileSource": {
         "description": "Source of the File.",
         "enum": [
            "SOURCE_UNSPECIFIED",
            "UPLOADED",
            "GENERATED",
            "REGISTERED"
         ],
         "title": "FileSource",
         "type": "string"
      },
      "FileState": {
         "description": "State for the lifecycle of a File.",
         "enum": [
            "STATE_UNSPECIFIED",
            "PROCESSING",
            "ACTIVE",
            "FAILED"
         ],
         "title": "FileState",
         "type": "string"
      },
      "FileStatus": {
         "additionalProperties": false,
         "description": "Status of a File that uses a common error model.",
         "properties": {
            "details": {
               "anyOf": [
                  {
                     "items": {
                        "additionalProperties": true,
                        "type": "object"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A list of messages that carry the error details. There is a common set of message types for APIs to use.",
               "title": "Details"
            },
            "message": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A list of messages that carry the error details. There is a common set of message types for APIs to use.",
               "title": "Message"
            },
            "code": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The status code. 0 for OK, 1 for CANCELLED",
               "title": "Code"
            }
         },
         "title": "FileStatus",
         "type": "object"
      },
      "FunctionCall": {
         "additionalProperties": false,
         "description": "A function call.",
         "properties": {
            "id": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The unique id of the function call. If populated, the client to execute the\n   `function_call` and return the response with the matching `id`.",
               "title": "Id"
            },
            "args": {
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
               "description": "Optional. The function parameters and values in JSON object format. See [FunctionDeclaration.parameters] for parameter details.",
               "title": "Args"
            },
            "name": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The name of the function to call. Matches [FunctionDeclaration.name].",
               "title": "Name"
            },
            "partialArgs": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/PartialArg"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The partial argument value of the function call. If provided, represents the arguments/fields that are streamed incrementally. This field is not supported in Gemini API.",
               "title": "Partialargs"
            },
            "willContinue": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Whether this is the last part of the FunctionCall. If true, another partial message for the current FunctionCall is expected to follow. This field is not supported in Gemini API.",
               "title": "Willcontinue"
            }
         },
         "title": "FunctionCall",
         "type": "object"
      },
      "FunctionResponse": {
         "additionalProperties": false,
         "description": "A function response.",
         "properties": {
            "willContinue": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Signals that function call continues, and more responses will be returned, turning the function call into a generator. Is only applicable to NON_BLOCKING function calls (see FunctionDeclaration.behavior for details), ignored otherwise. If false, the default, future responses will not be considered. Is only applicable to NON_BLOCKING function calls, is ignored otherwise. If set to false, future responses will not be considered. It is allowed to return empty `response` with `will_continue=False` to signal that the function call is finished.",
               "title": "Willcontinue"
            },
            "scheduling": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FunctionResponseScheduling"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Specifies how the response should be scheduled in the conversation. Only applicable to NON_BLOCKING function calls, is ignored otherwise. Defaults to WHEN_IDLE."
            },
            "parts": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/FunctionResponsePart"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "List of parts that constitute a function response. Each part may\n      have a different IANA MIME type.",
               "title": "Parts"
            },
            "id": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The id of the function call this response is for. Populated by the client to match the corresponding function call `id`.",
               "title": "Id"
            },
            "name": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. The name of the function to call. Matches [FunctionDeclaration.name] and [FunctionCall.name].",
               "title": "Name"
            },
            "response": {
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
               "description": "Required. The function response in JSON object format. Use \"output\" key to specify function output and \"error\" key to specify error details (if any). If \"output\" and \"error\" keys are not specified, then whole \"response\" is treated as function output.",
               "title": "Response"
            }
         },
         "title": "FunctionResponse",
         "type": "object"
      },
      "FunctionResponseBlob": {
         "additionalProperties": false,
         "description": "Raw media bytes for function response.\n\nText should not be sent as raw bytes, use the FunctionResponse.response\nfield.",
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
               "description": "Required. The IANA standard MIME type of the source data.",
               "title": "Mimetype"
            },
            "data": {
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
               "description": "Required. Inline media bytes.",
               "title": "Data"
            },
            "displayName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Display name of the blob.\n      Used to provide a label or filename to distinguish blobs.",
               "title": "Displayname"
            }
         },
         "title": "FunctionResponseBlob",
         "type": "object"
      },
      "FunctionResponseFileData": {
         "additionalProperties": false,
         "description": "URI based data for function response.",
         "properties": {
            "fileUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. URI.",
               "title": "Fileuri"
            },
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
               "description": "Required. The IANA standard MIME type of the source data.",
               "title": "Mimetype"
            },
            "displayName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Display name of the file.\n      Used to provide a label or filename to distinguish files.",
               "title": "Displayname"
            }
         },
         "title": "FunctionResponseFileData",
         "type": "object"
      },
      "FunctionResponsePart": {
         "additionalProperties": false,
         "description": "A datatype containing media that is part of a `FunctionResponse` message.\n\nA `FunctionResponsePart` consists of data which has an associated datatype. A\n`FunctionResponsePart` can only contain one of the accepted types in\n`FunctionResponsePart.data`.\n\nA `FunctionResponsePart` must have a fixed IANA MIME type identifying the\ntype and subtype of the media if the `inline_data` field is filled with raw\nbytes.",
         "properties": {
            "inlineData": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FunctionResponseBlob"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Inline media bytes."
            },
            "fileData": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FunctionResponseFileData"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. URI based data."
            }
         },
         "title": "FunctionResponsePart",
         "type": "object"
      },
      "FunctionResponseScheduling": {
         "description": "Specifies how the response should be scheduled in the conversation.",
         "enum": [
            "SCHEDULING_UNSPECIFIED",
            "SILENT",
            "WHEN_IDLE",
            "INTERRUPT"
         ],
         "title": "FunctionResponseScheduling",
         "type": "string"
      },
      "Language": {
         "description": "Programming language of the `code`.",
         "enum": [
            "LANGUAGE_UNSPECIFIED",
            "PYTHON"
         ],
         "title": "Language",
         "type": "string"
      },
      "Outcome": {
         "description": "Outcome of the code execution.",
         "enum": [
            "OUTCOME_UNSPECIFIED",
            "OUTCOME_OK",
            "OUTCOME_FAILED",
            "OUTCOME_DEADLINE_EXCEEDED"
         ],
         "title": "Outcome",
         "type": "string"
      },
      "Part": {
         "additionalProperties": false,
         "description": "A datatype containing media content.\n\nExactly one field within a Part should be set, representing the specific type\nof content being conveyed. Using multiple fields within the same `Part`\ninstance is considered invalid.",
         "properties": {
            "mediaResolution": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/PartMediaResolution"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Media resolution for the input media.\n    "
            },
            "codeExecutionResult": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/CodeExecutionResult"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Result of executing the [ExecutableCode]."
            },
            "executableCode": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ExecutableCode"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Code generated by the model that is meant to be executed."
            },
            "fileData": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FileData"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. URI based data."
            },
            "functionCall": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FunctionCall"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. A predicted [FunctionCall] returned from the model that contains a string representing the [FunctionDeclaration.name] with the parameters and their values."
            },
            "functionResponse": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/FunctionResponse"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The result output of a [FunctionCall] that contains a string representing the [FunctionDeclaration.name] and a structured JSON object containing any output from the function call. It is used as context to the model."
            },
            "inlineData": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/Blob"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Inlined bytes data."
            },
            "text": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Text part (can be code).",
               "title": "Text"
            },
            "thought": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Indicates if the part is thought from the model.",
               "title": "Thought"
            },
            "thoughtSignature": {
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
               "description": "Optional. An opaque signature for the thought so it can be reused in subsequent requests.",
               "title": "Thoughtsignature"
            },
            "videoMetadata": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/VideoMetadata"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Video metadata. The metadata should only be specified while the video data is presented in inline_data or file_data."
            }
         },
         "title": "Part",
         "type": "object"
      },
      "PartMediaResolution": {
         "additionalProperties": false,
         "description": "Media resolution for the input media.",
         "properties": {
            "level": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/PartMediaResolutionLevel"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The tokenization quality used for given media.\n    "
            },
            "numTokens": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Specifies the required sequence length for media tokenization.\n    ",
               "title": "Numtokens"
            }
         },
         "title": "PartMediaResolution",
         "type": "object"
      },
      "PartMediaResolutionLevel": {
         "description": "The tokenization quality used for given media.",
         "enum": [
            "MEDIA_RESOLUTION_UNSPECIFIED",
            "MEDIA_RESOLUTION_LOW",
            "MEDIA_RESOLUTION_MEDIUM",
            "MEDIA_RESOLUTION_HIGH",
            "MEDIA_RESOLUTION_ULTRA_HIGH"
         ],
         "title": "PartMediaResolutionLevel",
         "type": "string"
      },
      "PartialArg": {
         "additionalProperties": false,
         "description": "Partial argument value of the function call.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "nullValue": {
               "anyOf": [
                  {
                     "const": "NULL_VALUE",
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Represents a null value.",
               "title": "Nullvalue"
            },
            "numberValue": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Represents a double value.",
               "title": "Numbervalue"
            },
            "stringValue": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Represents a string value.",
               "title": "Stringvalue"
            },
            "boolValue": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Represents a boolean value.",
               "title": "Boolvalue"
            },
            "jsonPath": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Required. A JSON Path (RFC 9535) to the argument being streamed. https://datatracker.ietf.org/doc/html/rfc9535. e.g. \"$.foo.bar[0].data\".",
               "title": "Jsonpath"
            },
            "willContinue": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Whether this is not the last part of the same json_path. If true, another PartialArg message for the current json_path is expected to follow.",
               "title": "Willcontinue"
            }
         },
         "title": "PartialArg",
         "type": "object"
      },
      "VideoMetadata": {
         "additionalProperties": false,
         "description": "Metadata describes the input video content.",
         "properties": {
            "endOffset": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The end offset of the video.",
               "title": "Endoffset"
            },
            "fps": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The frame rate of the video sent to the model. If not specified, the default value will be 1.0. The fps range is (0.0, 24.0].",
               "title": "Fps"
            },
            "startOffset": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. The start offset of the video.",
               "title": "Startoffset"
            }
         },
         "title": "VideoMetadata",
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
after_model_callback (Optional[AfterModelCallback])

after_tool_callback (Optional[AfterToolCallback])

before_model_callback (Optional[BeforeModelCallback])

before_tool_callback (Optional[BeforeToolCallback])

code_executor (Optional[BaseCodeExecutor])

disallow_transfer_to_parent (bool)

disallow_transfer_to_peers (bool)

generate_content_config (Optional[types.GenerateContentConfig])

global_instruction (Union[str, InstructionProvider])

include_contents (Literal['default', 'none'])

input_schema (Optional[type[BaseModel]])

instruction (Union[str, InstructionProvider])

model (Union[str, BaseLlm])

on_model_error_callback (Optional[OnModelErrorCallback])

on_tool_error_callback (Optional[OnToolErrorCallback])

output_key (Optional[str])

output_schema (Optional[type[BaseModel]])

planner (Optional[BasePlanner])

static_instruction (Optional[types.ContentUnion])

tools (list[ToolUnion])


**Validators:**
__model_validator_after»all fields

validate_generate_content_config»generate_content_config


***field*after_model_callback*:**AfterModelCallback**|**None**=**None*¶**
Callback or list of callbacks to be called after calling the LLM.

When a list of callbacks is provided, the callbacks will be called in the order they are listed until a callback does not return None.


**Parameters:**
**callback_context**– CallbackContext,

**llm_response**– LlmResponse, the actual model response.


**Returns:**
The content to return to the user. When present, the actual model response will be ignored and the provided content will be returned to user.


**Validated by:**
__model_validator_after


***field*after_tool_callback*:**AfterToolCallback**|**None**=**None*¶**
Callback or list of callbacks to be called after calling the tool.

When a list of callbacks is provided, the callbacks will be called in the order they are listed until a callback does not return None.


**Parameters:**
**tool**– The tool to be called.

**args**– The arguments to the tool.

**tool_context**– ToolContext,

**tool_response**– The response from the tool.


**Returns:**
When present, the returned dict will be used as tool result.


**Validated by:**
__model_validator_after


***field*before_model_callback*:**BeforeModelCallback**|**None**=**None*¶**
Callback or list of callbacks to be called before calling the LLM.

When a list of callbacks is provided, the callbacks will be called in the order they are listed until a callback does not return None.


**Parameters:**
**callback_context**– CallbackContext,

**llm_request**– LlmRequest, The raw model request. Callback can mutate the

**request.**


**Returns:**
The content to return to the user. When present, the model call will be skipped and the provided content will be returned to user.


**Validated by:**
__model_validator_after


***field*before_tool_callback*:**BeforeToolCallback**|**None**=**None*¶**
Callback or list of callbacks to be called before calling the tool.

When a list of callbacks is provided, the callbacks will be called in the order they are listed until a callback does not return None.


**Parameters:**
**tool**– The tool to be called.

**args**– The arguments to the tool.

**tool_context**– ToolContext,


**Returns:**
The tool response. When present, the returned tool response will be used and the framework will skip calling the actual tool.


**Validated by:**
__model_validator_after


***field*code_executor*:*[*BaseCodeExecutor**|**None**=**None*¶**
Allow agent to execute code blocks from model responses using the provided CodeExecutor.

Check out available code executions ingoogle.adk.code_executorpackage.

Note

To use model’s built-in code executor, use theBuiltInCodeExecutor.


**Validated by:**
__model_validator_after


***field*disallow_transfer_to_parent*:**bool**=**False*¶**
Disallows LLM-controlled transferring to the parent agent.

NOTE: Setting this as True also prevents this agent from continuing to reply to the end-user, and will transfer control back to the parent agent in the next turn. This behavior prevents one-way transfer, in which end-user may be stuck with one agent that cannot transfer to other agents in the agent tree.


**Validated by:**
__model_validator_after


***field*disallow_transfer_to_peers*:**bool**=**False*¶**
Disallows LLM-controlled transferring to the peer agents.


**Validated by:**
__model_validator_after


***field*generate_content_config*:**types.GenerateContentConfig**|**None**=**None*¶**
The additional content generation configurations.

NOTE: not all fields are usable, e.g. tools must be configured viatools, thinking_config can be configured here or via theplanner. If both are set, the planner’s configuration takes precedence.

For example: use this config to adjust model temperature, configure safety settings, etc.


**Validated by:**
__model_validator_after

validate_generate_content_config


***field*global_instruction*:**str**|**InstructionProvider**=**''*¶**
Instructions for all the agents in the entire agent tree.

DEPRECATED: This field is deprecated and will be removed in a future version. Use GlobalInstructionPlugin instead, which provides the same functionality at the App level. See migration guide for details.

ONLY the global_instruction in root agent will take effect.

For example: use global_instruction to make all agents have a stable identity or personality.


**Validated by:**
__model_validator_after


***field*include_contents*:**Literal**[**'default'**,**'none'**]**=**'default'*¶**
Controls content inclusion in model requests.


**Options:**
default: Model receives relevant conversation history none: Model receives no prior history, operates solely on current instruction and input


**Validated by:**
__model_validator_after


***field*input_schema*:**type**[**BaseModel**]**|**None**=**None*¶**
The input schema when agent is used as a tool.


**Validated by:**
__model_validator_after


***field*instruction*:**str**|**InstructionProvider**=**''*¶**
Dynamic instructions for the LLM model, guiding the agent’s behavior.

These instructions can contain placeholders like {variable_name} that will be resolved at runtime using session state and context.

**Behavior depends on static_instruction:**- If static_instruction is None: instruction goes to system_instruction - If static_instruction is set: instruction goes to user content in the request

This allows for context caching optimization where static content (static_instruction) comes first in the prompt, followed by dynamic content (instruction).


**Validated by:**
__model_validator_after


***field*model*:**str**|*[*BaseLlm**=**''*¶**
The model to use for the agent.

When not set, the agent will inherit the model from its ancestor. If no ancestor provides a model, the agent uses the default model configured via LlmAgent.set_default_model. The built-in default is gemini-2.5-flash.


**Validated by:**
__model_validator_after


***field*on_model_error_callback*:**OnModelErrorCallback**|**None**=**None*¶**
Callback or list of callbacks to be called when a model call encounters an error.

When a list of callbacks is provided, the callbacks will be called in the order they are listed until a callback does not return None.


**Parameters:**
**callback_context**– CallbackContext,

**llm_request**– LlmRequest, The raw model request.

**error**– The error from the model call.


**Returns:**
The content to return to the user. When present, the error will be ignored and the provided content will be returned to user.


**Validated by:**
__model_validator_after


***field*on_tool_error_callback*:**OnToolErrorCallback**|**None**=**None*¶**
Callback or list of callbacks to be called when a tool call encounters an error.

When a list of callbacks is provided, the callbacks will be called in the order they are listed until a callback does not return None.


**Parameters:**
**tool**– The tool to be called.

**args**– The arguments to the tool.

**tool_context**– ToolContext,

**error**– The error from the tool call.


**Returns:**
When present, the returned dict will be used as tool result.


**Validated by:**
__model_validator_after


***field*output_key*:**str**|**None**=**None*¶**
The key in session state to store the output of the agent.

Typically use cases: - Extracts agent reply for later use, such as in tools, callbacks, etc. - Connects agents to coordinate with each other.


**Validated by:**
__model_validator_after


***field*output_schema*:**type**[**BaseModel**]**|**None**=**None*¶**
The output schema when agent replies.

Note

When this is set, agent can ONLY reply and CANNOT use any tools, such as function tools, RAGs, agent transfer, etc.


**Validated by:**
__model_validator_after


***field*planner*:*[*BasePlanner**|**None**=**None*¶**
Instructs the agent to make a plan and execute it step by step.

Note

To use model’s built-in thinking features, set thethinking_configfield ingoogle.adk.planners.built_in_planner.


**Validated by:**
__model_validator_after


***field*static_instruction*:**types.ContentUnion**|**None**=**None*¶**
Static instruction content sent literally as system instruction at the beginning.

This field is for content that never changes and doesn’t contain placeholders. It’s sent directly to the model without any processing or variable substitution.

This field is primarily for context caching optimization. Static instructions are sent as system instruction at the beginning of the request, allowing for improved performance when the static portion remains unchanged. Live API has its own cache mechanism, thus this field doesn’t work with Live API.

**Impact on instruction field:**- When static_instruction is None: instruction → system_instruction - When static_instruction is set: instruction → user content (after static content)

**Context Caching:**-**Implicit Cache**: Automatic caching by model providers (no config needed) -**Explicit Cache**: Cache explicitly created by user for instructions, tools and contents

See below for more information of Implicit Cache and Explicit Cache Gemini API:[https://ai.google.dev/gemini-api/docs/caching?lang=pythonVertex API:[https://cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview

Setting static_instruction alone does NOT enable caching automatically. For explicit caching control, configure context_cache_config at App level.

**Content Support:**Accepts types.ContentUnion which includes: - str: Simple text instruction - types.Content: Rich content object - types.Part: Single part (text, inline_data, file_data, etc.) - PIL.Image.Image: Image object - types.File: File reference - list[PartUnion]: List of parts

**Examples:**[``[`python # Simple string instruction static_instruction = “You are a helpful assistant.”

# Rich content with files static_instruction = types.Content(

role=’user’, parts=[

types.Part(text=’You are a helpful assistant.’), types.Part(file_data=types.FileData(…))

]


## )¶

**Validated by:**
__model_validator_after


***field*tools*:**list**[**ToolUnion**]**[Optional]*¶**
Tools available to this agent.


**Validated by:**
__model_validator_after


**config_type¶**
alias ofLlmAgentConfig


***classmethod*set_default_model(*model*)¶**
Overrides the default model used when an agent has no model set.


**Return type:**
None


***validator*validate_generate_content_config*»**generate_content_config*¶**

**Return type:**
GenerateContentConfig


***async*canonical_global_instruction(*ctx*)¶**
The resolved self.instruction field to construct global instruction.

This method is only for use by Agent Development Kit.


**Return type:**
tuple[str,bool]


**Parameters:**
**ctx**– The context to retrieve the session state.


**Returns:**
A tuple of (instruction, bypass_state_injection). instruction: The resolved self.global_instruction field. bypass_state_injection: Whether the instruction is based on InstructionProvider.


***async*canonical_instruction(*ctx*)¶**
The resolved self.instruction field to construct instruction for this agent.

This method is only for use by Agent Development Kit.


**Return type:**
tuple[str,bool]


**Parameters:**
**ctx**– The context to retrieve the session state.


**Returns:**
A tuple of (instruction, bypass_state_injection). instruction: The resolved self.instruction field. bypass_state_injection: Whether the instruction is based on InstructionProvider.


***async*canonical_tools(*ctx**=**None*)¶**
The resolved self.tools field as a list of BaseTool based on the context.

This method is only for use by Agent Development Kit.


**Return type:**
list[[BaseTool]


**model_post_init(*_LlmAgent__context*)¶**
Provides a warning if multiple thinking configurations are found.


**Return type:**
None


**DEFAULT_MODEL*:**ClassVar**[**str**]**=**'gemini-2.5-flash'*¶**
System default model used when no model is set on an agent.


***property*canonical_after_model_callbacks*:**list**[**Callable**[**[**CallbackContext**,**LlmResponse**]**,**Awaitable**[**LlmResponse**|**None**]**|**LlmResponse**|**None**]**]*¶**
The resolved self.after_model_callback field as a list of _SingleAfterModelCallback.

This method is only for use by Agent Development Kit.


***property*canonical_after_tool_callbacks*:**list**[**Callable**[**[*[*BaseTool**,**dict**[**str**,**Any**]**,*[*ToolContext**,**dict**]**,**Awaitable**[**dict**|**None**]**|**dict**|**None**]**|**list**[**Callable**[**[*[*BaseTool**,**dict**[**str**,**Any**]**,*[*ToolContext**,**dict**]**,**Awaitable**[**dict**|**None**]**|**dict**|**None**]**]**]*¶**
The resolved self.after_tool_callback field as a list of AfterToolCallback.

This method is only for use by Agent Development Kit.


***property*canonical_before_model_callbacks*:**list**[**Callable**[**[**CallbackContext**,**LlmRequest**]**,**Awaitable**[**LlmResponse**|**None**]**|**LlmResponse**|**None**]**]*¶**
The resolved self.before_model_callback field as a list of _SingleBeforeModelCallback.

This method is only for use by Agent Development Kit.


***property*canonical_before_tool_callbacks*:**list**[**Callable**[**[*[*BaseTool**,**dict**[**str**,**Any**]**,*[*ToolContext**]**,**Awaitable**[**dict**|**None**]**|**dict**|**None**]**|**list**[**Callable**[**[*[*BaseTool**,**dict**[**str**,**Any**]**,*[*ToolContext**]**,**Awaitable**[**dict**|**None**]**|**dict**|**None**]**]**]*¶**
The resolved self.before_tool_callback field as a list of BeforeToolCallback.

This method is only for use by Agent Development Kit.


***property*canonical_model*:*[*BaseLlm*¶**
The resolved self.model field as BaseLlm.

This method is only for use by Agent Development Kit.


***property*canonical_on_model_error_callbacks*:**list**[**Callable**[**[**CallbackContext**,**LlmRequest**,**Exception**]**,**Awaitable**[**LlmResponse**|**None**]**|**LlmResponse**|**None**]**]*¶**
The resolved self.on_model_error_callback field as a list of _SingleOnModelErrorCallback.

This method is only for use by Agent Development Kit.


***property*canonical_on_tool_error_callbacks*:**list**[**Callable**[**[*[*BaseTool**,**dict**[**str**,**Any**]**,*[*ToolContext**,**Exception**]**,**Awaitable**[**dict**|**None**]**|**dict**|**None**]**|**list**[**Callable**[**[*[*BaseTool**,**dict**[**str**,**Any**]**,*[*ToolContext**,**Exception**]**,**Awaitable**[**dict**|**None**]**|**dict**|**None**]**]**]*¶**
The resolved self.on_tool_error_callback field as a list of OnToolErrorCallback.

This method is only for use by Agent Development Kit.


***pydantic**model*google.adk.agents.LoopAgent¶**
Bases:[BaseAgent

A shell agent that run its sub-agents in a loop.

When sub-agent generates an event with escalate or max_iterations are reached, the loop agent will stop.


```
Show JSON schema{
   "title": "LoopAgent",
   "description": "A shell agent that run its sub-agents in a loop.\n\nWhen sub-agent generates an event with escalate or max_iterations are\nreached, the loop agent will stop.",
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
      },
      "max_iterations": {
         "anyOf": [
            {
               "type": "integer"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Max Iterations"
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
max_iterations (Optional[int])


**Validators:**

***field*max_iterations*:**int**|**None**=**None*¶**
The maximum number of iterations to run the loop agent.

If not set, the loop agent will run indefinitely until a sub-agent escalates.


**config_type¶**
alias ofLoopAgentConfig


***class*google.adk.agents.McpInstructionProvider(*connection_params*,*prompt_name*,*errlog=<_io.TextIOWrapper**name='<stderr>'**mode='w'**encoding='utf-8'>*)¶**
Bases:Callable[[ReadonlyContext],str|Awaitable[str]]

Fetches agent instructions from an MCP server.

Initializes the McpInstructionProvider.


**Parameters:**
**connection_params**– Parameters for connecting to the MCP server.

**prompt_name**– The name of the MCP Prompt to fetch.

**errlog**– TextIO stream for error logging.


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