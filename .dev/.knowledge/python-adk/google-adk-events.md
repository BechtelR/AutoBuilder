# google.adk.events module¶

***pydantic**model*google.adk.events.Event¶**
Bases:LlmResponse

Represents an event in a conversation between agents and users.

It is used to store the content of the conversation, as well as the actions taken by the agents like function calls, etc.


```
Show JSON schema{
   "title": "Event",
   "description": "Represents an event in a conversation between agents and users.\n\nIt is used to store the content of the conversation, as well as the actions\ntaken by the agents like function calls, etc.",
   "type": "object",
   "properties": {
      "modelVersion": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Modelversion"
      },
      "content": {
         "anyOf": [
            {
               "$ref": "#/$defs/Content"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "groundingMetadata": {
         "anyOf": [
            {
               "$ref": "#/$defs/GroundingMetadata"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "partial": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Partial"
      },
      "turnComplete": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Turncomplete"
      },
      "finishReason": {
         "anyOf": [
            {
               "$ref": "#/$defs/FinishReason"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "errorCode": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Errorcode"
      },
      "errorMessage": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Errormessage"
      },
      "interrupted": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Interrupted"
      },
      "customMetadata": {
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
         "title": "Custommetadata"
      },
      "usageMetadata": {
         "anyOf": [
            {
               "$ref": "#/$defs/GenerateContentResponseUsageMetadata"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "liveSessionResumptionUpdate": {
         "anyOf": [
            {
               "$ref": "#/$defs/LiveServerSessionResumptionUpdate"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "inputTranscription": {
         "anyOf": [
            {
               "$ref": "#/$defs/Transcription"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "outputTranscription": {
         "anyOf": [
            {
               "$ref": "#/$defs/Transcription"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "avgLogprobs": {
         "anyOf": [
            {
               "type": "number"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Avglogprobs"
      },
      "logprobsResult": {
         "anyOf": [
            {
               "$ref": "#/$defs/LogprobsResult"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "cacheMetadata": {
         "anyOf": [
            {
               "$ref": "#/$defs/CacheMetadata"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "citationMetadata": {
         "anyOf": [
            {
               "$ref": "#/$defs/CitationMetadata"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "interactionId": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Interactionid"
      },
      "invocationId": {
         "default": "",
         "title": "Invocationid",
         "type": "string"
      },
      "author": {
         "title": "Author",
         "type": "string"
      },
      "actions": {
         "$ref": "#/$defs/EventActions"
      },
      "longRunningToolIds": {
         "anyOf": [
            {
               "items": {
                  "type": "string"
               },
               "type": "array",
               "uniqueItems": true
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Longrunningtoolids"
      },
      "branch": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Branch"
      },
      "id": {
         "default": "",
         "title": "Id",
         "type": "string"
      },
      "timestamp": {
         "title": "Timestamp",
         "type": "number"
      }
   },
   "$defs": {
      "APIKey": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "apiKey"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "in": {
               "$ref": "#/$defs/APIKeyIn"
            },
            "name": {
               "title": "Name",
               "type": "string"
            }
         },
         "required": [
            "in",
            "name"
         ],
         "title": "APIKey",
         "type": "object"
      },
      "APIKeyIn": {
         "enum": [
            "query",
            "header",
            "cookie"
         ],
         "title": "APIKeyIn",
         "type": "string"
      },
      "AuthConfig": {
         "additionalProperties": true,
         "description": "The auth config sent by tool asking client to collect auth credentials and\n\nadk and client will help to fill in the response",
         "properties": {
            "authScheme": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/APIKey"
                  },
                  {
                     "$ref": "#/$defs/HTTPBase"
                  },
                  {
                     "$ref": "#/$defs/OAuth2"
                  },
                  {
                     "$ref": "#/$defs/OpenIdConnect"
                  },
                  {
                     "$ref": "#/$defs/HTTPBearer"
                  },
                  {
                     "$ref": "#/$defs/OpenIdConnectWithConfig"
                  }
               ],
               "title": "Authscheme"
            },
            "rawAuthCredential": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/AuthCredential"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "exchangedAuthCredential": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/AuthCredential"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "credentialKey": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Credentialkey"
            }
         },
         "required": [
            "authScheme"
         ],
         "title": "AuthConfig",
         "type": "object"
      },
      "AuthCredential": {
         "additionalProperties": true,
         "description": "Data class representing an authentication credential.\n\nTo exchange for the actual credential, please use\nCredentialExchanger.exchange_credential().\n\nExamples: API Key Auth\nAuthCredential(\n    auth_type=AuthCredentialTypes.API_KEY,\n    api_key=\"1234\",\n)\n\nExample: HTTP Auth\nAuthCredential(\n    auth_type=AuthCredentialTypes.HTTP,\n    http=HttpAuth(\n        scheme=\"basic\",\n        credentials=HttpCredentials(username=\"user\", password=\"password\"),\n    ),\n)\n\nExample: OAuth2 Bearer Token in HTTP Header\nAuthCredential(\n    auth_type=AuthCredentialTypes.HTTP,\n    http=HttpAuth(\n        scheme=\"bearer\",\n        credentials=HttpCredentials(token=\"eyAkaknabna....\"),\n    ),\n)\n\nExample: OAuth2 Auth with Authorization Code Flow\nAuthCredential(\n    auth_type=AuthCredentialTypes.OAUTH2,\n    oauth2=OAuth2Auth(\n        client_id=\"1234\",\n        client_secret=\"secret\",\n    ),\n)\n\nExample: OpenID Connect Auth\nAuthCredential(\n    auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,\n    oauth2=OAuth2Auth(\n        client_id=\"1234\",\n        client_secret=\"secret\",\n        redirect_uri=\"https://example.com\",\n        scopes=[\"scope1\", \"scope2\"],\n    ),\n)\n\nExample: Auth with resource reference\nAuthCredential(\n    auth_type=AuthCredentialTypes.API_KEY,\n    resource_ref=\"projects/1234/locations/us-central1/resources/resource1\",\n)",
         "properties": {
            "authType": {
               "$ref": "#/$defs/AuthCredentialTypes"
            },
            "resourceRef": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Resourceref"
            },
            "apiKey": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Apikey"
            },
            "http": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/HttpAuth"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "serviceAccount": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ServiceAccount"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "oauth2": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuth2Auth"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            }
         },
         "required": [
            "authType"
         ],
         "title": "AuthCredential",
         "type": "object"
      },
      "AuthCredentialTypes": {
         "description": "Represents the type of authentication credential.",
         "enum": [
            "apiKey",
            "http",
            "oauth2",
            "openIdConnect",
            "serviceAccount"
         ],
         "title": "AuthCredentialTypes",
         "type": "string"
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
      "CacheMetadata": {
         "additionalProperties": false,
         "description": "Metadata for context cache associated with LLM responses.\n\nThis class stores cache identification, usage tracking, and lifecycle\ninformation for a particular cache instance. It can be in two states:\n\n1. Active cache state: cache_name is set, all fields populated\n2. Fingerprint-only state: cache_name is None, only fingerprint and\n   contents_count are set for prefix matching\n\nToken counts (cached and total) are available in the LlmResponse.usage_metadata\nand should be accessed from there to avoid duplication.\n\nAttributes:\n    cache_name: The full resource name of the cached content (e.g.,\n        'projects/123/locations/us-central1/cachedContents/456').\n        None when no active cache exists (fingerprint-only state).\n    expire_time: Unix timestamp when the cache expires. None when no\n        active cache exists.\n    fingerprint: Hash of cacheable contents (instruction + tools + contents).\n        Always present for prefix matching.\n    invocations_used: Number of invocations this cache has been used for.\n        None when no active cache exists.\n    contents_count: Number of contents. When active cache exists, this is\n        the count of cached contents. When no active cache exists, this is\n        the total count of contents in the request.\n    created_at: Unix timestamp when the cache was created. None when\n        no active cache exists.",
         "properties": {
            "cache_name": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Full resource name of the cached content (None if no active cache)",
               "title": "Cache Name"
            },
            "expire_time": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Unix timestamp when cache expires (None if no active cache)",
               "title": "Expire Time"
            },
            "fingerprint": {
               "description": "Hash of cacheable contents used to detect changes",
               "title": "Fingerprint",
               "type": "string"
            },
            "invocations_used": {
               "anyOf": [
                  {
                     "minimum": 0,
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Number of invocations this cache has been used for (None if no active cache)",
               "title": "Invocations Used"
            },
            "contents_count": {
               "description": "Number of contents (cached contents when active cache exists, total contents in request when no active cache)",
               "minimum": 0,
               "title": "Contents Count",
               "type": "integer"
            },
            "created_at": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Unix timestamp when cache was created (None if no active cache)",
               "title": "Created At"
            }
         },
         "required": [
            "fingerprint",
            "contents_count"
         ],
         "title": "CacheMetadata",
         "type": "object"
      },
      "Citation": {
         "additionalProperties": false,
         "description": "Source attributions for content.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "endIndex": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. End index into the content.",
               "title": "Endindex"
            },
            "license": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. License of the attribution.",
               "title": "License"
            },
            "publicationDate": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/GoogleTypeDate"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Publication date of the attribution."
            },
            "startIndex": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Start index into the content.",
               "title": "Startindex"
            },
            "title": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Title of the attribution.",
               "title": "Title"
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
               "description": "Output only. Url reference of the attribution.",
               "title": "Uri"
            }
         },
         "title": "Citation",
         "type": "object"
      },
      "CitationMetadata": {
         "additionalProperties": false,
         "description": "Citation information when the model quotes another source.",
         "properties": {
            "citations": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/Citation"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Contains citation information when the model directly quotes, at\n      length, from another source. Can include traditional websites and code\n      repositories.\n      ",
               "title": "Citations"
            }
         },
         "title": "CitationMetadata",
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
      "EventActions": {
         "additionalProperties": false,
         "description": "Represents the actions attached to an event.",
         "properties": {
            "skipSummarization": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Skipsummarization"
            },
            "stateDelta": {
               "additionalProperties": true,
               "title": "Statedelta",
               "type": "object"
            },
            "artifactDelta": {
               "additionalProperties": {
                  "type": "integer"
               },
               "title": "Artifactdelta",
               "type": "object"
            },
            "transferToAgent": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Transfertoagent"
            },
            "escalate": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Escalate"
            },
            "requestedAuthConfigs": {
               "additionalProperties": {
                  "$ref": "#/$defs/AuthConfig"
               },
               "title": "Requestedauthconfigs",
               "type": "object"
            },
            "requestedToolConfirmations": {
               "additionalProperties": {
                  "$ref": "#/$defs/ToolConfirmation"
               },
               "title": "Requestedtoolconfirmations",
               "type": "object"
            },
            "compaction": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/EventCompaction"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "endOfAgent": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Endofagent"
            },
            "agentState": {
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
               "title": "Agentstate"
            },
            "rewindBeforeInvocationId": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Rewindbeforeinvocationid"
            }
         },
         "title": "EventActions",
         "type": "object"
      },
      "EventCompaction": {
         "additionalProperties": false,
         "description": "The compaction of the events.",
         "properties": {
            "startTimestamp": {
               "title": "Starttimestamp",
               "type": "number"
            },
            "endTimestamp": {
               "title": "Endtimestamp",
               "type": "number"
            },
            "compactedContent": {
               "$ref": "#/$defs/Content"
            }
         },
         "required": [
            "startTimestamp",
            "endTimestamp",
            "compactedContent"
         ],
         "title": "EventCompaction",
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
      "FinishReason": {
         "description": "Output only. The reason why the model stopped generating tokens.\n\nIf empty, the model has not stopped generating the tokens.",
         "enum": [
            "FINISH_REASON_UNSPECIFIED",
            "STOP",
            "MAX_TOKENS",
            "SAFETY",
            "RECITATION",
            "LANGUAGE",
            "OTHER",
            "BLOCKLIST",
            "PROHIBITED_CONTENT",
            "SPII",
            "MALFORMED_FUNCTION_CALL",
            "IMAGE_SAFETY",
            "UNEXPECTED_TOOL_CALL",
            "IMAGE_PROHIBITED_CONTENT",
            "NO_IMAGE",
            "IMAGE_RECITATION",
            "IMAGE_OTHER"
         ],
         "title": "FinishReason",
         "type": "string"
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
      "GenerateContentResponseUsageMetadata": {
         "additionalProperties": false,
         "description": "Usage metadata about the content generation request and response.\n\nThis message provides a detailed breakdown of token usage and other relevant\nmetrics. This data type is not supported in Gemini API.",
         "properties": {
            "cacheTokensDetails": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/ModalityTokenCount"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. A detailed breakdown of the token count for each modality in the cached content.",
               "title": "Cachetokensdetails"
            },
            "cachedContentTokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The number of tokens in the cached content that was used for this request.",
               "title": "Cachedcontenttokencount"
            },
            "candidatesTokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The total number of tokens in the generated candidates.",
               "title": "Candidatestokencount"
            },
            "candidatesTokensDetails": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/ModalityTokenCount"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. A detailed breakdown of the token count for each modality in the generated candidates.",
               "title": "Candidatestokensdetails"
            },
            "promptTokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The total number of tokens in the prompt. This includes any text, images, or other media provided in the request. When `cached_content` is set, this also includes the number of tokens in the cached content.",
               "title": "Prompttokencount"
            },
            "promptTokensDetails": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/ModalityTokenCount"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. A detailed breakdown of the token count for each modality in the prompt.",
               "title": "Prompttokensdetails"
            },
            "thoughtsTokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The number of tokens that were part of the model's generated \"thoughts\" output, if applicable.",
               "title": "Thoughtstokencount"
            },
            "toolUsePromptTokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The number of tokens in the results from tool executions, which are provided back to the model as input, if applicable.",
               "title": "Tooluseprompttokencount"
            },
            "toolUsePromptTokensDetails": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/ModalityTokenCount"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. A detailed breakdown by modality of the token counts from the results of tool executions, which are provided back to the model as input.",
               "title": "Tooluseprompttokensdetails"
            },
            "totalTokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The total number of tokens for the entire request. This is the sum of `prompt_token_count`, `candidates_token_count`, `tool_use_prompt_token_count`, and `thoughts_token_count`.",
               "title": "Totaltokencount"
            },
            "trafficType": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/TrafficType"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The traffic type for this request."
            }
         },
         "title": "GenerateContentResponseUsageMetadata",
         "type": "object"
      },
      "GoogleTypeDate": {
         "additionalProperties": false,
         "description": "Represents a whole or partial calendar date, such as a birthday.\n\nThe time of day and time zone are either specified elsewhere or are\ninsignificant. The date is relative to the Gregorian Calendar. This can\nrepresent one of the following: * A full date, with non-zero year, month, and\nday values. * A month and day, with a zero year (for example, an anniversary).\n* A year on its own, with a zero month and a zero day. * A year and month,\nwith a zero day (for example, a credit card expiration date). Related types: *\ngoogle.type.TimeOfDay * google.type.DateTime * google.protobuf.Timestamp. This\ndata type is not supported in Gemini API.",
         "properties": {
            "day": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Day of a month. Must be from 1 to 31 and valid for the year and month, or 0 to specify a year by itself or a year and month where the day isn't significant.",
               "title": "Day"
            },
            "month": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Month of a year. Must be from 1 to 12, or 0 to specify a year without a month and day.",
               "title": "Month"
            },
            "year": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Year of the date. Must be from 1 to 9999, or 0 to specify a date without a year.",
               "title": "Year"
            }
         },
         "title": "GoogleTypeDate",
         "type": "object"
      },
      "GroundingChunk": {
         "additionalProperties": false,
         "description": "Grounding chunk.",
         "properties": {
            "maps": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/GroundingChunkMaps"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Grounding chunk from Google Maps. This field is not supported in Gemini API."
            },
            "retrievedContext": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/GroundingChunkRetrievedContext"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Grounding chunk from context retrieved by the retrieval tools. This field is not supported in Gemini API."
            },
            "web": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/GroundingChunkWeb"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Grounding chunk from the web."
            }
         },
         "title": "GroundingChunk",
         "type": "object"
      },
      "GroundingChunkMaps": {
         "additionalProperties": false,
         "description": "Chunk from Google Maps. This data type is not supported in Gemini API.",
         "properties": {
            "placeAnswerSources": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/GroundingChunkMapsPlaceAnswerSources"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Sources used to generate the place answer. This includes review snippets and photos that were used to generate the answer, as well as uris to flag content."
            },
            "placeId": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "This Place's resource name, in `places/{place_id}` format. Can be used to look up the Place.",
               "title": "Placeid"
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
               "description": "Text of the place answer.",
               "title": "Text"
            },
            "title": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Title of the place.",
               "title": "Title"
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
               "description": "URI reference of the place.",
               "title": "Uri"
            }
         },
         "title": "GroundingChunkMaps",
         "type": "object"
      },
      "GroundingChunkMapsPlaceAnswerSources": {
         "additionalProperties": false,
         "description": "Sources used to generate the place answer.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "flagContentUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A link where users can flag a problem with the generated answer.",
               "title": "Flagcontenturi"
            },
            "reviewSnippets": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/GroundingChunkMapsPlaceAnswerSourcesReviewSnippet"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Snippets of reviews that are used to generate the answer.",
               "title": "Reviewsnippets"
            }
         },
         "title": "GroundingChunkMapsPlaceAnswerSources",
         "type": "object"
      },
      "GroundingChunkMapsPlaceAnswerSourcesAuthorAttribution": {
         "additionalProperties": false,
         "description": "Author attribution for a photo or review.\n\nThis data type is not supported in Gemini API.",
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
               "description": "Name of the author of the Photo or Review.",
               "title": "Displayname"
            },
            "photoUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Profile photo URI of the author of the Photo or Review.",
               "title": "Photouri"
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
               "description": "URI of the author of the Photo or Review.",
               "title": "Uri"
            }
         },
         "title": "GroundingChunkMapsPlaceAnswerSourcesAuthorAttribution",
         "type": "object"
      },
      "GroundingChunkMapsPlaceAnswerSourcesReviewSnippet": {
         "additionalProperties": false,
         "description": "Encapsulates a review snippet.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "authorAttribution": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/GroundingChunkMapsPlaceAnswerSourcesAuthorAttribution"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "This review's author."
            },
            "flagContentUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A link where users can flag a problem with the review.",
               "title": "Flagcontenturi"
            },
            "googleMapsUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A link to show the review on Google Maps.",
               "title": "Googlemapsuri"
            },
            "relativePublishTimeDescription": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A string of formatted recent time, expressing the review time relative to the current time in a form appropriate for the language and country.",
               "title": "Relativepublishtimedescription"
            },
            "review": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A reference representing this place review which may be used to look up this place review again.",
               "title": "Review"
            },
            "reviewId": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Id of the review referencing the place.",
               "title": "Reviewid"
            },
            "title": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Title of the review.",
               "title": "Title"
            }
         },
         "title": "GroundingChunkMapsPlaceAnswerSourcesReviewSnippet",
         "type": "object"
      },
      "GroundingChunkRetrievedContext": {
         "additionalProperties": false,
         "description": "Chunk from context retrieved by the retrieval tools.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "documentName": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The full document name for the referenced Vertex AI Search document.",
               "title": "Documentname"
            },
            "ragChunk": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/RagChunk"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Additional context for the RAG retrieval result. This is only populated when using the RAG retrieval tool."
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
               "description": "Text of the attribution.",
               "title": "Text"
            },
            "title": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Title of the attribution.",
               "title": "Title"
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
               "description": "URI reference of the attribution.",
               "title": "Uri"
            }
         },
         "title": "GroundingChunkRetrievedContext",
         "type": "object"
      },
      "GroundingChunkWeb": {
         "additionalProperties": false,
         "description": "Chunk from the web.",
         "properties": {
            "domain": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Domain of the (original) URI. This field is not supported in Gemini API.",
               "title": "Domain"
            },
            "title": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Title of the chunk.",
               "title": "Title"
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
               "description": "URI reference of the chunk.",
               "title": "Uri"
            }
         },
         "title": "GroundingChunkWeb",
         "type": "object"
      },
      "GroundingMetadata": {
         "additionalProperties": false,
         "description": "Metadata returned to client when grounding is enabled.",
         "properties": {
            "googleMapsWidgetContextToken": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Output only. Resource name of the Google Maps widget context token to be used with the PlacesContextElement widget to render contextual data. This is populated only for Google Maps grounding. This field is not supported in Gemini API.",
               "title": "Googlemapswidgetcontexttoken"
            },
            "groundingChunks": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/GroundingChunk"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "List of supporting references retrieved from specified grounding source.",
               "title": "Groundingchunks"
            },
            "groundingSupports": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/GroundingSupport"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. List of grounding support.",
               "title": "Groundingsupports"
            },
            "retrievalMetadata": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/RetrievalMetadata"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Output only. Retrieval metadata."
            },
            "retrievalQueries": {
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
               "description": "Optional. Queries executed by the retrieval tools. This field is not supported in Gemini API.",
               "title": "Retrievalqueries"
            },
            "searchEntryPoint": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/SearchEntryPoint"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Google search entry for the following-up web searches."
            },
            "sourceFlaggingUris": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/GroundingMetadataSourceFlaggingUri"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Output only. List of source flagging uris. This is currently populated only for Google Maps grounding. This field is not supported in Gemini API.",
               "title": "Sourceflagginguris"
            },
            "webSearchQueries": {
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
               "description": "Optional. Web search queries for the following-up web search.",
               "title": "Websearchqueries"
            }
         },
         "title": "GroundingMetadata",
         "type": "object"
      },
      "GroundingMetadataSourceFlaggingUri": {
         "additionalProperties": false,
         "description": "Source content flagging uri for a place or review.\n\nThis is currently populated only for Google Maps grounding. This data type is\nnot supported in Gemini API.",
         "properties": {
            "flagContentUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "A link where users can flag a problem with the source (place or review).",
               "title": "Flagcontenturi"
            },
            "sourceId": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Id of the place or review.",
               "title": "Sourceid"
            }
         },
         "title": "GroundingMetadataSourceFlaggingUri",
         "type": "object"
      },
      "GroundingSupport": {
         "additionalProperties": false,
         "description": "Grounding support.",
         "properties": {
            "confidenceScores": {
               "anyOf": [
                  {
                     "items": {
                        "type": "number"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Confidence score of the support references. Ranges from 0 to 1. 1 is the most confident. For Gemini 2.0 and before, this list must have the same size as the grounding_chunk_indices. For Gemini 2.5 and after, this list will be empty and should be ignored.",
               "title": "Confidencescores"
            },
            "groundingChunkIndices": {
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
               "description": "A list of indices (into 'grounding_chunk') specifying the citations associated with the claim. For instance [1,3,4] means that grounding_chunk[1], grounding_chunk[3], grounding_chunk[4] are the retrieved content attributed to the claim.",
               "title": "Groundingchunkindices"
            },
            "segment": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/Segment"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Segment of the content this support belongs to."
            }
         },
         "title": "GroundingSupport",
         "type": "object"
      },
      "HTTPBase": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "http"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "scheme": {
               "title": "Scheme",
               "type": "string"
            }
         },
         "required": [
            "scheme"
         ],
         "title": "HTTPBase",
         "type": "object"
      },
      "HTTPBearer": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "http"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "scheme": {
               "const": "bearer",
               "default": "bearer",
               "title": "Scheme",
               "type": "string"
            },
            "bearerFormat": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Bearerformat"
            }
         },
         "title": "HTTPBearer",
         "type": "object"
      },
      "HttpAuth": {
         "additionalProperties": true,
         "description": "The credentials and metadata for HTTP authentication.",
         "properties": {
            "scheme": {
               "title": "Scheme",
               "type": "string"
            },
            "credentials": {
               "$ref": "#/$defs/HttpCredentials"
            },
            "additionalHeaders": {
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
               "title": "Additionalheaders"
            }
         },
         "required": [
            "scheme",
            "credentials"
         ],
         "title": "HttpAuth",
         "type": "object"
      },
      "HttpCredentials": {
         "additionalProperties": true,
         "description": "Represents the secret token value for HTTP authentication, like user name, password, oauth token, etc.",
         "properties": {
            "username": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Username"
            },
            "password": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Password"
            },
            "token": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Token"
            }
         },
         "title": "HttpCredentials",
         "type": "object"
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
      "LiveServerSessionResumptionUpdate": {
         "additionalProperties": false,
         "description": "Update of the session resumption state.\n\nOnly sent if `session_resumption` was set in the connection config.",
         "properties": {
            "newHandle": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "New handle that represents state that can be resumed. Empty if `resumable`=false.",
               "title": "Newhandle"
            },
            "resumable": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "True if session can be resumed at this point. It might be not possible to resume session at some points. In that case we send update empty new_handle and resumable=false. Example of such case could be model executing function calls or just generating. Resuming session (using previous session token) in such state will result in some data loss.",
               "title": "Resumable"
            },
            "lastConsumedClientMessageIndex": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Index of last message sent by client that is included in state represented by this SessionResumptionToken. Only sent when `SessionResumptionConfig.transparent` is set.\n\nPresence of this index allows users to transparently reconnect and avoid issue of losing some part of realtime audio input/video. If client wishes to temporarily disconnect (for example as result of receiving GoAway) they can do it without losing state by buffering messages sent since last `SessionResmumptionTokenUpdate`. This field will enable them to limit buffering (avoid keeping all requests in RAM).\n\nNote: This should not be used for when resuming a session at some time later -- in those cases partial audio and video frames arelikely not needed.",
               "title": "Lastconsumedclientmessageindex"
            }
         },
         "title": "LiveServerSessionResumptionUpdate",
         "type": "object"
      },
      "LogprobsResult": {
         "additionalProperties": false,
         "description": "Logprobs Result",
         "properties": {
            "chosenCandidates": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/LogprobsResultCandidate"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Length = total number of decoding steps. The chosen candidates may or may not be in top_candidates.",
               "title": "Chosencandidates"
            },
            "topCandidates": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/LogprobsResultTopCandidates"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Length = total number of decoding steps.",
               "title": "Topcandidates"
            }
         },
         "title": "LogprobsResult",
         "type": "object"
      },
      "LogprobsResultCandidate": {
         "additionalProperties": false,
         "description": "Candidate for the logprobs token and score.",
         "properties": {
            "logProbability": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The candidate's log probability.",
               "title": "Logprobability"
            },
            "token": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The candidate's token string value.",
               "title": "Token"
            },
            "tokenId": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The candidate's token id value.",
               "title": "Tokenid"
            }
         },
         "title": "LogprobsResultCandidate",
         "type": "object"
      },
      "LogprobsResultTopCandidates": {
         "additionalProperties": false,
         "description": "Candidates with top log probabilities at each decoding step.",
         "properties": {
            "candidates": {
               "anyOf": [
                  {
                     "items": {
                        "$ref": "#/$defs/LogprobsResultCandidate"
                     },
                     "type": "array"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Sorted by log probability in descending order.",
               "title": "Candidates"
            }
         },
         "title": "LogprobsResultTopCandidates",
         "type": "object"
      },
      "MediaModality": {
         "description": "Server content modalities.",
         "enum": [
            "MODALITY_UNSPECIFIED",
            "TEXT",
            "IMAGE",
            "VIDEO",
            "AUDIO",
            "DOCUMENT"
         ],
         "title": "MediaModality",
         "type": "string"
      },
      "ModalityTokenCount": {
         "additionalProperties": false,
         "description": "Represents token counting info for a single modality.",
         "properties": {
            "modality": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/MediaModality"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The modality associated with this token count."
            },
            "tokenCount": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Number of tokens.",
               "title": "Tokencount"
            }
         },
         "title": "ModalityTokenCount",
         "type": "object"
      },
      "OAuth2": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "oauth2"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "flows": {
               "$ref": "#/$defs/OAuthFlows"
            }
         },
         "required": [
            "flows"
         ],
         "title": "OAuth2",
         "type": "object"
      },
      "OAuth2Auth": {
         "additionalProperties": true,
         "description": "Represents credential value and its metadata for a OAuth2 credential.",
         "properties": {
            "clientId": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Clientid"
            },
            "clientSecret": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Clientsecret"
            },
            "authUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Authuri"
            },
            "state": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "State"
            },
            "redirectUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Redirecturi"
            },
            "authResponseUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Authresponseuri"
            },
            "authCode": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Authcode"
            },
            "accessToken": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Accesstoken"
            },
            "refreshToken": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshtoken"
            },
            "expiresAt": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Expiresat"
            },
            "expiresIn": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Expiresin"
            },
            "audience": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Audience"
            },
            "tokenEndpointAuthMethod": {
               "anyOf": [
                  {
                     "enum": [
                        "client_secret_basic",
                        "client_secret_post",
                        "client_secret_jwt",
                        "private_key_jwt"
                     ],
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": "client_secret_basic",
               "title": "Tokenendpointauthmethod"
            }
         },
         "title": "OAuth2Auth",
         "type": "object"
      },
      "OAuthFlowAuthorizationCode": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "authorizationUrl": {
               "title": "Authorizationurl",
               "type": "string"
            },
            "tokenUrl": {
               "title": "Tokenurl",
               "type": "string"
            }
         },
         "required": [
            "authorizationUrl",
            "tokenUrl"
         ],
         "title": "OAuthFlowAuthorizationCode",
         "type": "object"
      },
      "OAuthFlowClientCredentials": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "tokenUrl": {
               "title": "Tokenurl",
               "type": "string"
            }
         },
         "required": [
            "tokenUrl"
         ],
         "title": "OAuthFlowClientCredentials",
         "type": "object"
      },
      "OAuthFlowImplicit": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "authorizationUrl": {
               "title": "Authorizationurl",
               "type": "string"
            }
         },
         "required": [
            "authorizationUrl"
         ],
         "title": "OAuthFlowImplicit",
         "type": "object"
      },
      "OAuthFlowPassword": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "tokenUrl": {
               "title": "Tokenurl",
               "type": "string"
            }
         },
         "required": [
            "tokenUrl"
         ],
         "title": "OAuthFlowPassword",
         "type": "object"
      },
      "OAuthFlows": {
         "additionalProperties": true,
         "properties": {
            "implicit": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowImplicit"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "password": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowPassword"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "clientCredentials": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowClientCredentials"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "authorizationCode": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowAuthorizationCode"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            }
         },
         "title": "OAuthFlows",
         "type": "object"
      },
      "OpenIdConnect": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "openIdConnect"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "openIdConnectUrl": {
               "title": "Openidconnecturl",
               "type": "string"
            }
         },
         "required": [
            "openIdConnectUrl"
         ],
         "title": "OpenIdConnect",
         "type": "object"
      },
      "OpenIdConnectWithConfig": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "openIdConnect"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "authorization_endpoint": {
               "title": "Authorization Endpoint",
               "type": "string"
            },
            "token_endpoint": {
               "title": "Token Endpoint",
               "type": "string"
            },
            "userinfo_endpoint": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Userinfo Endpoint"
            },
            "revocation_endpoint": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Revocation Endpoint"
            },
            "token_endpoint_auth_methods_supported": {
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
               "title": "Token Endpoint Auth Methods Supported"
            },
            "grant_types_supported": {
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
               "title": "Grant Types Supported"
            },
            "scopes": {
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
               "title": "Scopes"
            }
         },
         "required": [
            "authorization_endpoint",
            "token_endpoint"
         ],
         "title": "OpenIdConnectWithConfig",
         "type": "object"
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
      "RagChunk": {
         "additionalProperties": false,
         "description": "A RagChunk includes the content of a chunk of a RagFile, and associated metadata.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "pageSpan": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/RagChunkPageSpan"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "If populated, represents where the chunk starts and ends in the document."
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
               "description": "The content of the chunk.",
               "title": "Text"
            }
         },
         "title": "RagChunk",
         "type": "object"
      },
      "RagChunkPageSpan": {
         "additionalProperties": false,
         "description": "Represents where the chunk starts and ends in the document.\n\nThis data type is not supported in Gemini API.",
         "properties": {
            "firstPage": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Page where chunk starts in the document. Inclusive. 1-indexed.",
               "title": "Firstpage"
            },
            "lastPage": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Page where chunk ends in the document. Inclusive. 1-indexed.",
               "title": "Lastpage"
            }
         },
         "title": "RagChunkPageSpan",
         "type": "object"
      },
      "RetrievalMetadata": {
         "additionalProperties": false,
         "description": "Metadata related to retrieval in the grounding flow.",
         "properties": {
            "googleSearchDynamicRetrievalScore": {
               "anyOf": [
                  {
                     "type": "number"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Score indicating how likely information from Google Search could help answer the prompt. The score is in the range `[0, 1]`, where 0 is the least likely and 1 is the most likely. This score is only populated when Google Search grounding and dynamic retrieval is enabled. It will be compared to the threshold to determine whether to trigger Google Search.",
               "title": "Googlesearchdynamicretrievalscore"
            }
         },
         "title": "RetrievalMetadata",
         "type": "object"
      },
      "SearchEntryPoint": {
         "additionalProperties": false,
         "description": "Google search entry point.",
         "properties": {
            "renderedContent": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Optional. Web content snippet that can be embedded in a web page or an app webview.",
               "title": "Renderedcontent"
            },
            "sdkBlob": {
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
               "description": "Optional. Base64 encoded JSON representing array of tuple.",
               "title": "Sdkblob"
            }
         },
         "title": "SearchEntryPoint",
         "type": "object"
      },
      "SecuritySchemeType": {
         "enum": [
            "apiKey",
            "http",
            "oauth2",
            "openIdConnect"
         ],
         "title": "SecuritySchemeType",
         "type": "string"
      },
      "Segment": {
         "additionalProperties": false,
         "description": "Segment of the content.",
         "properties": {
            "endIndex": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. End index in the given Part, measured in bytes. Offset from the start of the Part, exclusive, starting at zero.",
               "title": "Endindex"
            },
            "partIndex": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. The index of a Part object within its parent Content object.",
               "title": "Partindex"
            },
            "startIndex": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "Output only. Start index in the given Part, measured in bytes. Offset from the start of the Part, inclusive, starting at zero.",
               "title": "Startindex"
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
               "description": "Output only. The text corresponding to the segment from the response.",
               "title": "Text"
            }
         },
         "title": "Segment",
         "type": "object"
      },
      "ServiceAccount": {
         "additionalProperties": true,
         "description": "Represents Google Service Account configuration.",
         "properties": {
            "serviceAccountCredential": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ServiceAccountCredential"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "scopes": {
               "items": {
                  "type": "string"
               },
               "title": "Scopes",
               "type": "array"
            },
            "useDefaultCredential": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": false,
               "title": "Usedefaultcredential"
            }
         },
         "required": [
            "scopes"
         ],
         "title": "ServiceAccount",
         "type": "object"
      },
      "ServiceAccountCredential": {
         "additionalProperties": true,
         "description": "Represents Google Service Account configuration.\n\nAttributes:\n  type: The type should be \"service_account\".\n  project_id: The project ID.\n  private_key_id: The ID of the private key.\n  private_key: The private key.\n  client_email: The client email.\n  client_id: The client ID.\n  auth_uri: The authorization URI.\n  token_uri: The token URI.\n  auth_provider_x509_cert_url: URL for auth provider's X.509 cert.\n  client_x509_cert_url: URL for the client's X.509 cert.\n  universe_domain: The universe domain.\n\nExample:\n\n    config = ServiceAccountCredential(\n        type_=\"service_account\",\n        project_id=\"your_project_id\",\n        private_key_id=\"your_private_key_id\",\n        private_key=\"-----BEGIN PRIVATE KEY-----...\",\n        client_email=\"...@....iam.gserviceaccount.com\",\n        client_id=\"your_client_id\",\n        auth_uri=\"https://accounts.google.com/o/oauth2/auth\",\n        token_uri=\"https://oauth2.googleapis.com/token\",\n        auth_provider_x509_cert_url=\"https://www.googleapis.com/oauth2/v1/certs\",\n        client_x509_cert_url=\"https://www.googleapis.com/robot/v1/metadata/x509/...\",\n        universe_domain=\"googleapis.com\"\n    )\n\n\n    config = ServiceAccountConfig.model_construct(**{\n        ...service account config dict\n    })",
         "properties": {
            "type": {
               "default": "",
               "title": "Type",
               "type": "string"
            },
            "projectId": {
               "title": "Projectid",
               "type": "string"
            },
            "privateKeyId": {
               "title": "Privatekeyid",
               "type": "string"
            },
            "privateKey": {
               "title": "Privatekey",
               "type": "string"
            },
            "clientEmail": {
               "title": "Clientemail",
               "type": "string"
            },
            "clientId": {
               "title": "Clientid",
               "type": "string"
            },
            "authUri": {
               "title": "Authuri",
               "type": "string"
            },
            "tokenUri": {
               "title": "Tokenuri",
               "type": "string"
            },
            "authProviderX509CertUrl": {
               "title": "Authproviderx509Certurl",
               "type": "string"
            },
            "clientX509CertUrl": {
               "title": "Clientx509Certurl",
               "type": "string"
            },
            "universeDomain": {
               "title": "Universedomain",
               "type": "string"
            }
         },
         "required": [
            "projectId",
            "privateKeyId",
            "privateKey",
            "clientEmail",
            "clientId",
            "authUri",
            "tokenUri",
            "authProviderX509CertUrl",
            "clientX509CertUrl",
            "universeDomain"
         ],
         "title": "ServiceAccountCredential",
         "type": "object"
      },
      "ToolConfirmation": {
         "additionalProperties": false,
         "description": "Represents a tool confirmation configuration.",
         "properties": {
            "hint": {
               "default": "",
               "title": "Hint",
               "type": "string"
            },
            "confirmed": {
               "default": false,
               "title": "Confirmed",
               "type": "boolean"
            },
            "payload": {
               "anyOf": [
                  {},
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Payload"
            }
         },
         "title": "ToolConfirmation",
         "type": "object"
      },
      "TrafficType": {
         "description": "Output only.\n\nThe traffic type for this request. This enum is not supported in Gemini API.",
         "enum": [
            "TRAFFIC_TYPE_UNSPECIFIED",
            "ON_DEMAND",
            "PROVISIONED_THROUGHPUT"
         ],
         "title": "TrafficType",
         "type": "string"
      },
      "Transcription": {
         "additionalProperties": false,
         "description": "Audio transcription in Server Conent.",
         "properties": {
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
               "description": "Transcription text.\n      ",
               "title": "Text"
            },
            "finished": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "description": "The bool indicates the end of the transcription.\n      ",
               "title": "Finished"
            }
         },
         "title": "Transcription",
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
      "author"
   ]
}
```


**Fields:**
actions (google.adk.events.event_actions.EventActions)

author (str)

branch (str | None)

id (str)

invocation_id (str)

long_running_tool_ids (set[str] | None)

timestamp (float)


***field*actions*:*[*EventActions**[Optional]*¶**
The actions taken by the agent.


***field*author*:**str**[Required]*¶**
‘user’ or the name of the agent, indicating who appended the event to the session.


***field*branch*:**str**|**None**=**None*¶**
The branch of the event.

The format is like agent_1.agent_2.agent_3, where agent_1 is the parent of agent_2, and agent_2 is the parent of agent_3.

Branch is used when multiple sub-agent shouldn’t see their peer agents’ conversation history.


***field*id*:**str**=**''*¶**
The unique identifier of the event.


***field*invocation_id*:**str**=**''**(alias**'invocationId')*¶**
The invocation ID of the event. Should be non-empty before appending to a session.


***field*long_running_tool_ids*:**set**[**str**]**|**None**=**None**(alias**'longRunningToolIds')*¶**
Set of ids of the long running function calls. Agent client will know from this field about which function call is long running. only valid for function call event


***field*timestamp*:**float**[Optional]*¶**
The timestamp of the event.


***static*new_id()¶**

**get_function_calls()¶**
Returns the function calls in the event.


**Return type:**
list[FunctionCall]


**get_function_responses()¶**
Returns the function responses in the event.


**Return type:**
list[FunctionResponse]


**has_trailing_code_execution_result()¶**
Returns whether the event has a trailing code execution result.


**Return type:**
bool


**is_final_response()¶**
Returns whether the event is the final response of an agent.

NOTE: This method is ONLY for use by Agent Development Kit.

Note that when multiple agents participate in one invocation, there could be one event hasis_final_response()as True for each participating agent.


**Return type:**
bool


**model_post_init(*_Event__context*)¶**
Post initialization logic for the event.


***pydantic**model*google.adk.events.EventActions¶**
Bases:BaseModel

Represents the actions attached to an event.


```
Show JSON schema{
   "title": "EventActions",
   "description": "Represents the actions attached to an event.",
   "type": "object",
   "properties": {
      "skipSummarization": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Skipsummarization"
      },
      "stateDelta": {
         "additionalProperties": true,
         "title": "Statedelta",
         "type": "object"
      },
      "artifactDelta": {
         "additionalProperties": {
            "type": "integer"
         },
         "title": "Artifactdelta",
         "type": "object"
      },
      "transferToAgent": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Transfertoagent"
      },
      "escalate": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Escalate"
      },
      "requestedAuthConfigs": {
         "additionalProperties": {
            "$ref": "#/$defs/AuthConfig"
         },
         "title": "Requestedauthconfigs",
         "type": "object"
      },
      "requestedToolConfirmations": {
         "additionalProperties": {
            "$ref": "#/$defs/ToolConfirmation"
         },
         "title": "Requestedtoolconfirmations",
         "type": "object"
      },
      "compaction": {
         "anyOf": [
            {
               "$ref": "#/$defs/EventCompaction"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "endOfAgent": {
         "anyOf": [
            {
               "type": "boolean"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Endofagent"
      },
      "agentState": {
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
         "title": "Agentstate"
      },
      "rewindBeforeInvocationId": {
         "anyOf": [
            {
               "type": "string"
            },
            {
               "type": "null"
            }
         ],
         "default": null,
         "title": "Rewindbeforeinvocationid"
      }
   },
   "$defs": {
      "APIKey": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "apiKey"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "in": {
               "$ref": "#/$defs/APIKeyIn"
            },
            "name": {
               "title": "Name",
               "type": "string"
            }
         },
         "required": [
            "in",
            "name"
         ],
         "title": "APIKey",
         "type": "object"
      },
      "APIKeyIn": {
         "enum": [
            "query",
            "header",
            "cookie"
         ],
         "title": "APIKeyIn",
         "type": "string"
      },
      "AuthConfig": {
         "additionalProperties": true,
         "description": "The auth config sent by tool asking client to collect auth credentials and\n\nadk and client will help to fill in the response",
         "properties": {
            "authScheme": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/APIKey"
                  },
                  {
                     "$ref": "#/$defs/HTTPBase"
                  },
                  {
                     "$ref": "#/$defs/OAuth2"
                  },
                  {
                     "$ref": "#/$defs/OpenIdConnect"
                  },
                  {
                     "$ref": "#/$defs/HTTPBearer"
                  },
                  {
                     "$ref": "#/$defs/OpenIdConnectWithConfig"
                  }
               ],
               "title": "Authscheme"
            },
            "rawAuthCredential": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/AuthCredential"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "exchangedAuthCredential": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/AuthCredential"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "credentialKey": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Credentialkey"
            }
         },
         "required": [
            "authScheme"
         ],
         "title": "AuthConfig",
         "type": "object"
      },
      "AuthCredential": {
         "additionalProperties": true,
         "description": "Data class representing an authentication credential.\n\nTo exchange for the actual credential, please use\nCredentialExchanger.exchange_credential().\n\nExamples: API Key Auth\nAuthCredential(\n    auth_type=AuthCredentialTypes.API_KEY,\n    api_key=\"1234\",\n)\n\nExample: HTTP Auth\nAuthCredential(\n    auth_type=AuthCredentialTypes.HTTP,\n    http=HttpAuth(\n        scheme=\"basic\",\n        credentials=HttpCredentials(username=\"user\", password=\"password\"),\n    ),\n)\n\nExample: OAuth2 Bearer Token in HTTP Header\nAuthCredential(\n    auth_type=AuthCredentialTypes.HTTP,\n    http=HttpAuth(\n        scheme=\"bearer\",\n        credentials=HttpCredentials(token=\"eyAkaknabna....\"),\n    ),\n)\n\nExample: OAuth2 Auth with Authorization Code Flow\nAuthCredential(\n    auth_type=AuthCredentialTypes.OAUTH2,\n    oauth2=OAuth2Auth(\n        client_id=\"1234\",\n        client_secret=\"secret\",\n    ),\n)\n\nExample: OpenID Connect Auth\nAuthCredential(\n    auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,\n    oauth2=OAuth2Auth(\n        client_id=\"1234\",\n        client_secret=\"secret\",\n        redirect_uri=\"https://example.com\",\n        scopes=[\"scope1\", \"scope2\"],\n    ),\n)\n\nExample: Auth with resource reference\nAuthCredential(\n    auth_type=AuthCredentialTypes.API_KEY,\n    resource_ref=\"projects/1234/locations/us-central1/resources/resource1\",\n)",
         "properties": {
            "authType": {
               "$ref": "#/$defs/AuthCredentialTypes"
            },
            "resourceRef": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Resourceref"
            },
            "apiKey": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Apikey"
            },
            "http": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/HttpAuth"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "serviceAccount": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ServiceAccount"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "oauth2": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuth2Auth"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            }
         },
         "required": [
            "authType"
         ],
         "title": "AuthCredential",
         "type": "object"
      },
      "AuthCredentialTypes": {
         "description": "Represents the type of authentication credential.",
         "enum": [
            "apiKey",
            "http",
            "oauth2",
            "openIdConnect",
            "serviceAccount"
         ],
         "title": "AuthCredentialTypes",
         "type": "string"
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
      "EventCompaction": {
         "additionalProperties": false,
         "description": "The compaction of the events.",
         "properties": {
            "startTimestamp": {
               "title": "Starttimestamp",
               "type": "number"
            },
            "endTimestamp": {
               "title": "Endtimestamp",
               "type": "number"
            },
            "compactedContent": {
               "$ref": "#/$defs/Content"
            }
         },
         "required": [
            "startTimestamp",
            "endTimestamp",
            "compactedContent"
         ],
         "title": "EventCompaction",
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
      "HTTPBase": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "http"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "scheme": {
               "title": "Scheme",
               "type": "string"
            }
         },
         "required": [
            "scheme"
         ],
         "title": "HTTPBase",
         "type": "object"
      },
      "HTTPBearer": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "http"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "scheme": {
               "const": "bearer",
               "default": "bearer",
               "title": "Scheme",
               "type": "string"
            },
            "bearerFormat": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Bearerformat"
            }
         },
         "title": "HTTPBearer",
         "type": "object"
      },
      "HttpAuth": {
         "additionalProperties": true,
         "description": "The credentials and metadata for HTTP authentication.",
         "properties": {
            "scheme": {
               "title": "Scheme",
               "type": "string"
            },
            "credentials": {
               "$ref": "#/$defs/HttpCredentials"
            },
            "additionalHeaders": {
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
               "title": "Additionalheaders"
            }
         },
         "required": [
            "scheme",
            "credentials"
         ],
         "title": "HttpAuth",
         "type": "object"
      },
      "HttpCredentials": {
         "additionalProperties": true,
         "description": "Represents the secret token value for HTTP authentication, like user name, password, oauth token, etc.",
         "properties": {
            "username": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Username"
            },
            "password": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Password"
            },
            "token": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Token"
            }
         },
         "title": "HttpCredentials",
         "type": "object"
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
      "OAuth2": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "oauth2"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "flows": {
               "$ref": "#/$defs/OAuthFlows"
            }
         },
         "required": [
            "flows"
         ],
         "title": "OAuth2",
         "type": "object"
      },
      "OAuth2Auth": {
         "additionalProperties": true,
         "description": "Represents credential value and its metadata for a OAuth2 credential.",
         "properties": {
            "clientId": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Clientid"
            },
            "clientSecret": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Clientsecret"
            },
            "authUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Authuri"
            },
            "state": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "State"
            },
            "redirectUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Redirecturi"
            },
            "authResponseUri": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Authresponseuri"
            },
            "authCode": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Authcode"
            },
            "accessToken": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Accesstoken"
            },
            "refreshToken": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshtoken"
            },
            "expiresAt": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Expiresat"
            },
            "expiresIn": {
               "anyOf": [
                  {
                     "type": "integer"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Expiresin"
            },
            "audience": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Audience"
            },
            "tokenEndpointAuthMethod": {
               "anyOf": [
                  {
                     "enum": [
                        "client_secret_basic",
                        "client_secret_post",
                        "client_secret_jwt",
                        "private_key_jwt"
                     ],
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": "client_secret_basic",
               "title": "Tokenendpointauthmethod"
            }
         },
         "title": "OAuth2Auth",
         "type": "object"
      },
      "OAuthFlowAuthorizationCode": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "authorizationUrl": {
               "title": "Authorizationurl",
               "type": "string"
            },
            "tokenUrl": {
               "title": "Tokenurl",
               "type": "string"
            }
         },
         "required": [
            "authorizationUrl",
            "tokenUrl"
         ],
         "title": "OAuthFlowAuthorizationCode",
         "type": "object"
      },
      "OAuthFlowClientCredentials": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "tokenUrl": {
               "title": "Tokenurl",
               "type": "string"
            }
         },
         "required": [
            "tokenUrl"
         ],
         "title": "OAuthFlowClientCredentials",
         "type": "object"
      },
      "OAuthFlowImplicit": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "authorizationUrl": {
               "title": "Authorizationurl",
               "type": "string"
            }
         },
         "required": [
            "authorizationUrl"
         ],
         "title": "OAuthFlowImplicit",
         "type": "object"
      },
      "OAuthFlowPassword": {
         "additionalProperties": true,
         "properties": {
            "refreshUrl": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Refreshurl"
            },
            "scopes": {
               "additionalProperties": {
                  "type": "string"
               },
               "default": {},
               "title": "Scopes",
               "type": "object"
            },
            "tokenUrl": {
               "title": "Tokenurl",
               "type": "string"
            }
         },
         "required": [
            "tokenUrl"
         ],
         "title": "OAuthFlowPassword",
         "type": "object"
      },
      "OAuthFlows": {
         "additionalProperties": true,
         "properties": {
            "implicit": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowImplicit"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "password": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowPassword"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "clientCredentials": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowClientCredentials"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "authorizationCode": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/OAuthFlowAuthorizationCode"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            }
         },
         "title": "OAuthFlows",
         "type": "object"
      },
      "OpenIdConnect": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "openIdConnect"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "openIdConnectUrl": {
               "title": "Openidconnecturl",
               "type": "string"
            }
         },
         "required": [
            "openIdConnectUrl"
         ],
         "title": "OpenIdConnect",
         "type": "object"
      },
      "OpenIdConnectWithConfig": {
         "additionalProperties": true,
         "properties": {
            "type": {
               "$ref": "#/$defs/SecuritySchemeType",
               "default": "openIdConnect"
            },
            "description": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Description"
            },
            "authorization_endpoint": {
               "title": "Authorization Endpoint",
               "type": "string"
            },
            "token_endpoint": {
               "title": "Token Endpoint",
               "type": "string"
            },
            "userinfo_endpoint": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Userinfo Endpoint"
            },
            "revocation_endpoint": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Revocation Endpoint"
            },
            "token_endpoint_auth_methods_supported": {
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
               "title": "Token Endpoint Auth Methods Supported"
            },
            "grant_types_supported": {
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
               "title": "Grant Types Supported"
            },
            "scopes": {
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
               "title": "Scopes"
            }
         },
         "required": [
            "authorization_endpoint",
            "token_endpoint"
         ],
         "title": "OpenIdConnectWithConfig",
         "type": "object"
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
      "SecuritySchemeType": {
         "enum": [
            "apiKey",
            "http",
            "oauth2",
            "openIdConnect"
         ],
         "title": "SecuritySchemeType",
         "type": "string"
      },
      "ServiceAccount": {
         "additionalProperties": true,
         "description": "Represents Google Service Account configuration.",
         "properties": {
            "serviceAccountCredential": {
               "anyOf": [
                  {
                     "$ref": "#/$defs/ServiceAccountCredential"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null
            },
            "scopes": {
               "items": {
                  "type": "string"
               },
               "title": "Scopes",
               "type": "array"
            },
            "useDefaultCredential": {
               "anyOf": [
                  {
                     "type": "boolean"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": false,
               "title": "Usedefaultcredential"
            }
         },
         "required": [
            "scopes"
         ],
         "title": "ServiceAccount",
         "type": "object"
      },
      "ServiceAccountCredential": {
         "additionalProperties": true,
         "description": "Represents Google Service Account configuration.\n\nAttributes:\n  type: The type should be \"service_account\".\n  project_id: The project ID.\n  private_key_id: The ID of the private key.\n  private_key: The private key.\n  client_email: The client email.\n  client_id: The client ID.\n  auth_uri: The authorization URI.\n  token_uri: The token URI.\n  auth_provider_x509_cert_url: URL for auth provider's X.509 cert.\n  client_x509_cert_url: URL for the client's X.509 cert.\n  universe_domain: The universe domain.\n\nExample:\n\n    config = ServiceAccountCredential(\n        type_=\"service_account\",\n        project_id=\"your_project_id\",\n        private_key_id=\"your_private_key_id\",\n        private_key=\"-----BEGIN PRIVATE KEY-----...\",\n        client_email=\"...@....iam.gserviceaccount.com\",\n        client_id=\"your_client_id\",\n        auth_uri=\"https://accounts.google.com/o/oauth2/auth\",\n        token_uri=\"https://oauth2.googleapis.com/token\",\n        auth_provider_x509_cert_url=\"https://www.googleapis.com/oauth2/v1/certs\",\n        client_x509_cert_url=\"https://www.googleapis.com/robot/v1/metadata/x509/...\",\n        universe_domain=\"googleapis.com\"\n    )\n\n\n    config = ServiceAccountConfig.model_construct(**{\n        ...service account config dict\n    })",
         "properties": {
            "type": {
               "default": "",
               "title": "Type",
               "type": "string"
            },
            "projectId": {
               "title": "Projectid",
               "type": "string"
            },
            "privateKeyId": {
               "title": "Privatekeyid",
               "type": "string"
            },
            "privateKey": {
               "title": "Privatekey",
               "type": "string"
            },
            "clientEmail": {
               "title": "Clientemail",
               "type": "string"
            },
            "clientId": {
               "title": "Clientid",
               "type": "string"
            },
            "authUri": {
               "title": "Authuri",
               "type": "string"
            },
            "tokenUri": {
               "title": "Tokenuri",
               "type": "string"
            },
            "authProviderX509CertUrl": {
               "title": "Authproviderx509Certurl",
               "type": "string"
            },
            "clientX509CertUrl": {
               "title": "Clientx509Certurl",
               "type": "string"
            },
            "universeDomain": {
               "title": "Universedomain",
               "type": "string"
            }
         },
         "required": [
            "projectId",
            "privateKeyId",
            "privateKey",
            "clientEmail",
            "clientId",
            "authUri",
            "tokenUri",
            "authProviderX509CertUrl",
            "clientX509CertUrl",
            "universeDomain"
         ],
         "title": "ServiceAccountCredential",
         "type": "object"
      },
      "ToolConfirmation": {
         "additionalProperties": false,
         "description": "Represents a tool confirmation configuration.",
         "properties": {
            "hint": {
               "default": "",
               "title": "Hint",
               "type": "string"
            },
            "confirmed": {
               "default": false,
               "title": "Confirmed",
               "type": "boolean"
            },
            "payload": {
               "anyOf": [
                  {},
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Payload"
            }
         },
         "title": "ToolConfirmation",
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
   "additionalProperties": false
}
```


**Fields:**
agent_state (dict[str, Any] | None)

artifact_delta (dict[str, int])

compaction (google.adk.events.event_actions.EventCompaction | None)

end_of_agent (bool | None)

escalate (bool | None)

requested_auth_configs (dict[str, google.adk.auth.auth_tool.AuthConfig])

requested_tool_confirmations (dict[str, google.adk.tools.tool_confirmation.ToolConfirmation])

rewind_before_invocation_id (str | None)

skip_summarization (bool | None)

state_delta (dict[str, object])

transfer_to_agent (str | None)


***field*agent_state*:**dict**[**str**,**Any**]**|**None**=**None**(alias**'agentState')*¶**
The agent state at the current event, used for checkpoint and resume. This should only be set by ADK workflow.


***field*artifact_delta*:**dict**[**str**,**int**]**[Optional]**(alias**'artifactDelta')*¶**
Indicates that the event is updating an artifact. key is the filename, value is the version.


***field*compaction*:**EventCompaction**|**None**=**None*¶**
The compaction of the events.


***field*end_of_agent*:**bool**|**None**=**None**(alias**'endOfAgent')*¶**
If true, the current agent has finished its current run. Note that there can be multiple events with end_of_agent=True for the same agent within one invocation when there is a loop. This should only be set by ADK workflow.


***field*escalate*:**bool**|**None**=**None*¶**
The agent is escalating to a higher level agent.


***field*requested_auth_configs*:**dict**[**str**,**AuthConfig**]**[Optional]**(alias**'requestedAuthConfigs')*¶**
Authentication configurations requested by tool responses.

This field will only be set by a tool response event indicating tool request auth credential. - Keys: The function call id. Since one function response event could contain multiple function responses that correspond to multiple function calls. Each function call could request different auth configs. This id is used to identify the function call. - Values: The requested auth config.


***field*requested_tool_confirmations*:**dict**[**str**,**ToolConfirmation**]**[Optional]**(alias**'requestedToolConfirmations')*¶**
A dict of tool confirmation requested by this event, keyed by function call id.


***field*rewind_before_invocation_id*:**str**|**None**=**None**(alias**'rewindBeforeInvocationId')*¶**
The invocation id to rewind to. This is only set for rewind event.


***field*skip_summarization*:**bool**|**None**=**None**(alias**'skipSummarization')*¶**
If true, it won’t call model to summarize function response.

Only used for function_response event.


***field*state_delta*:**dict**[**str**,**object**]**[Optional]**(alias**'stateDelta')*¶**
Indicates that the event is updating the state with the given delta.


***field*transfer_to_agent*:**str**|**None**=**None**(alias**'transferToAgent')*¶**
If set, the event transfers to the specified agent.


# google.adk.examples module¶

***class*google.adk.examples.BaseExampleProvider¶**
Bases:ABC

Base class for example providers.

This class defines the interface for providing examples for a given query.


***abstractmethod*get_examples(*query*)¶**
Returns a list of examples for a given query.


**Return type:**
list[[Example]


**Parameters:**
**query**– The query to get examples for.


**Returns:**
A list of Example objects.


***pydantic**model*google.adk.examples.Example¶**
Bases:BaseModel

A few-shot example.


**input¶**
The input content for the example.


**output¶**
The expected output content for the example.


```
Show JSON schema{
   "title": "Example",
   "description": "A few-shot example.\n\nAttributes:\n  input: The input content for the example.\n  output: The expected output content for the example.",
   "type": "object",
   "properties": {
      "input": {
         "$ref": "#/$defs/Content"
      },
      "output": {
         "items": {
            "$ref": "#/$defs/Content"
         },
         "title": "Output",
         "type": "array"
      }
   },
   "$defs": {
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
   "required": [
      "input",
      "output"
   ]
}
```


**Fields:**
input (google.genai.types.Content)

output (list[google.genai.types.Content])


***field*input*:**types.Content**[Required]*¶**

***field*output*:**list**[**types.Content**]**[Required]*¶**

***class*google.adk.examples.VertexAiExampleStore(*examples_store_name*)¶**
Bases:[BaseExampleProvider

Provides examples from Vertex example store.

Initializes the VertexAiExampleStore.


**Parameters:**
**examples_store_name**– The resource name of the vertex example store, in the format ofprojects/{project}/locations/{location}/exampleStores/{example_store}.


**get_examples(*query*)¶**
Returns a list of examples for a given query.


**Return type:**
list[[Example]


**Parameters:**
**query**– The query to get examples for.


**Returns:**
A list of Example objects.


# google.adk.flows module¶

# google.adk.memory module¶

***class*google.adk.memory.BaseMemoryService¶**
Bases:ABC

Base class for memory services.

The service provides functionalities to ingest sessions into memory so that the memory can be used for user queries.


***abstractmethod**async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***abstractmethod**async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query.


**Return type:**
SearchMemoryResponse


**Parameters:**
**app_name**– The name of the application.

**user_id**– The id of the user.

**query**– The query to search for.


**Returns:**
A SearchMemoryResponse containing the matching memories.


***class*google.adk.memory.InMemoryMemoryService¶**
Bases:[BaseMemoryService

An in-memory memory service for prototyping purpose only.

Uses keyword matching instead of semantic search.

This class is thread-safe, however, it should be used for testing and development only.


***async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query.


**Return type:**
SearchMemoryResponse


**Parameters:**
**app_name**– The name of the application.

**user_id**– The id of the user.

**query**– The query to search for.


**Returns:**
A SearchMemoryResponse containing the matching memories.


***class*google.adk.memory.VertexAiMemoryBankService(*project**=**None*,*location**=**None*,*agent_engine_id**=**None*,***,*express_mode_api_key**=**None*)¶**
Bases:[BaseMemoryService

Implementation of the BaseMemoryService using Vertex AI Memory Bank.

Initializes a VertexAiMemoryBankService.


**Parameters:**
**project**– The project ID of the Memory Bank to use.

**location**– The location of the Memory Bank to use.

**agent_engine_id**– The ID of the agent engine to use for the Memory Bank, e.g. ‘456’ in ‘projects/my-project/locations/us-central1/reasoningEngines/456’. To extract from api_resource.name, use:agent_engine.api_resource.name.split('/')[-1]

**express_mode_api_key**– The API key to use for Express Mode. If not provided, the API key from the GOOGLE_API_KEY environment variable will be used. It will only be used if GOOGLE_GENAI_USE_VERTEXAI is true. Do not use Google AI Studio API key for this field. For more details, visit[https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview


***async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query.


**Parameters:**
**app_name**– The name of the application.

**user_id**– The id of the user.

**query**– The query to search for.


**Returns:**
A SearchMemoryResponse containing the matching memories.


***class*google.adk.memory.VertexAiRagMemoryService(*rag_corpus**=**None*,*similarity_top_k**=**None*,*vector_distance_threshold**=**10*)¶**
Bases:[BaseMemoryService

A memory service that uses Vertex AI RAG for storage and retrieval.

Initializes a VertexAiRagMemoryService.


**Parameters:**
**rag_corpus**– The name of the Vertex AI RAG corpus to use. Format:projects/{project}/locations/{location}/ragCorpora/{rag_corpus_id}or{rag_corpus_id}

**similarity_top_k**– The number of contexts to retrieve.

**vector_distance_threshold**– Only returns contexts with vector distance smaller than the threshold.


***async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query using rag.retrieval_query.


**Return type:**
SearchMemoryResponse


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