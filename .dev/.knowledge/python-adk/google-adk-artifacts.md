# google.adk.artifacts module¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.artifacts

***class*google.adk.artifacts.BaseArtifactService¶**
Bases:ABC

Abstract base class for artifact services.


***abstractmethod**async*delete_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Deletes an artifact.


**Return type:**
None


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, delete the user-scoped artifact.


***abstractmethod**async*get_artifact_version(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets the metadata for a specific version of an artifact.


**Return type:**
Optional[ArtifactVersion]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, the artifact will be fetched from the user-scoped artifacts. Otherwise, it will be fetched from the specified session.

**version**– The version number of the artifact to retrieve. IfNone, the latest version will be returned.


**Returns:**
An ArtifactVersion object containing the metadata of the specified artifact version, orNoneif the artifact version is not found.


***abstractmethod**async*list_artifact_keys(***,*app_name*,*user_id*,*session_id**=**None*)¶**
Lists all the artifact filenames within a session.


**Return type:**
list[str]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**session_id**– The ID of the session.


**Returns:**
A list of artifact filenames. Ifsession_idis provided, returns both session-scoped and user-scoped artifact filenames. Ifsession_idisNone, returns user-scoped artifact filenames.


***abstractmethod**async*list_artifact_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions and their metadata for a specific artifact.


**Return type:**
list[ArtifactVersion]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, lists versions of the user-scoped artifact. Otherwise, lists versions of the artifact within the specified session.


**Returns:**
A list of ArtifactVersion objects, each representing a version of the artifact and its associated metadata.


***abstractmethod**async*list_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions of an artifact.


**Return type:**
list[int]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, only list the user-scoped artifacts versions.


**Returns:**
A list of all available versions of the artifact.


***abstractmethod**async*load_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.


**Return type:**
Optional[Part]


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**session_id**– The session ID. IfNone, load the user-scoped artifact.

**version**– The version of the artifact. If None, the latest version will be returned.


**Returns:**
The artifact or None if not found.


***abstractmethod**async*save_artifact(***,*app_name*,*user_id*,*filename*,*artifact*,*session_id**=**None*,*custom_metadata**=**None*)¶**
Saves an artifact to the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename. After saving the artifact, a revision ID is returned to identify the artifact version.


**Return type:**
int


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**artifact**– The artifact to save. If the artifact consists offile_data, the artifact service assumes its content has been uploaded separately, and this method will associate thefile_datawith the artifact if necessary.

**session_id**– The session ID. IfNone, the artifact is user-scoped.

**custom_metadata**– custom metadata to associate with the artifact.


**Returns:**
The revision ID. The first version of the artifact has a revision ID of 0. This is incremented by 1 after each successful save.


***class*google.adk.artifacts.FileArtifactService(*root_dir*)¶**
Bases:[BaseArtifactService

Stores filesystem-backed artifacts beneath a configurable root directory.

Initializes the file-based artifact service.


**Parameters:**
**root_dir**– The directory that will contain artifact data.


***async*delete_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Deletes an artifact.


**Return type:**
None


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. Leave unset for user-scoped artifacts.


***async*get_artifact_version(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets metadata for a specific artifact version.


**Return type:**
Optional[ArtifactVersion]


***async*list_artifact_keys(***,*app_name*,*user_id*,*session_id**=**None*)¶**
Lists all the artifact filenames within a session.


**Return type:**
list[str]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**session_id**– The ID of the session.


**Returns:**
A list of artifact filenames. Ifsession_idis provided, returns both session-scoped and user-scoped artifact filenames. Ifsession_idisNone, returns user-scoped artifact filenames.


***async*list_artifact_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists metadata for each artifact version on disk.


**Return type:**
list[ArtifactVersion]


***async*list_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions stored for an artifact.


**Return type:**
list[int]


***async*load_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.


**Return type:**
Optional[Part]


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**session_id**– The session ID. IfNone, load the user-scoped artifact.

**version**– The version of the artifact. If None, the latest version will be returned.


**Returns:**
The artifact or None if not found.


***async*save_artifact(***,*app_name*,*user_id*,*filename*,*artifact*,*session_id**=**None*,*custom_metadata**=**None*)¶**
Persists an artifact to disk.

Filenames may be simple ("report.txt"), nested ("images/photo.png"), or explicitly user-scoped ("user:shared/diagram.png"). All values are interpreted relative to the computed scope root; absolute paths or inputs that traverse outside that root (for example"../../secret.txt") raiseValueError.


**Return type:**
int


***class*google.adk.artifacts.GcsArtifactService(*bucket_name*,*****kwargs*)¶**
Bases:[BaseArtifactService

An artifact service implementation using Google Cloud Storage (GCS).

Initializes the GcsArtifactService.


**Parameters:**
**bucket_name**– The name of the bucket to use.

****kwargs**– Keyword arguments to pass to the Google Cloud Storage client.


***async*delete_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Deletes an artifact.


**Return type:**
None


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, delete the user-scoped artifact.


***async*get_artifact_version(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets the metadata for a specific version of an artifact.


**Return type:**
Optional[ArtifactVersion]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, the artifact will be fetched from the user-scoped artifacts. Otherwise, it will be fetched from the specified session.

**version**– The version number of the artifact to retrieve. IfNone, the latest version will be returned.


**Returns:**
An ArtifactVersion object containing the metadata of the specified artifact version, orNoneif the artifact version is not found.


***async*list_artifact_keys(***,*app_name*,*user_id*,*session_id**=**None*)¶**
Lists all the artifact filenames within a session.


**Return type:**
list[str]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**session_id**– The ID of the session.


**Returns:**
A list of artifact filenames. Ifsession_idis provided, returns both session-scoped and user-scoped artifact filenames. Ifsession_idisNone, returns user-scoped artifact filenames.


***async*list_artifact_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions and their metadata for a specific artifact.


**Return type:**
list[ArtifactVersion]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, lists versions of the user-scoped artifact. Otherwise, lists versions of the artifact within the specified session.


**Returns:**
A list of ArtifactVersion objects, each representing a version of the artifact and its associated metadata.


***async*list_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions of an artifact.


**Return type:**
list[int]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, only list the user-scoped artifacts versions.


**Returns:**
A list of all available versions of the artifact.


***async*load_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.


**Return type:**
Optional[Part]


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**session_id**– The session ID. IfNone, load the user-scoped artifact.

**version**– The version of the artifact. If None, the latest version will be returned.


**Returns:**
The artifact or None if not found.


***async*save_artifact(***,*app_name*,*user_id*,*filename*,*artifact*,*session_id**=**None*,*custom_metadata**=**None*)¶**
Saves an artifact to the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename. After saving the artifact, a revision ID is returned to identify the artifact version.


**Return type:**
int


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**artifact**– The artifact to save. If the artifact consists offile_data, the artifact service assumes its content has been uploaded separately, and this method will associate thefile_datawith the artifact if necessary.

**session_id**– The session ID. IfNone, the artifact is user-scoped.

**custom_metadata**– custom metadata to associate with the artifact.


**Returns:**
The revision ID. The first version of the artifact has a revision ID of 0. This is incremented by 1 after each successful save.


***pydantic**model*google.adk.artifacts.InMemoryArtifactService¶**
Bases:[BaseArtifactService,BaseModel

An in-memory implementation of the artifact service.

It is not suitable for multi-threaded production environments. Use it for testing and development only.


```
Show JSON schema{
   "title": "InMemoryArtifactService",
   "description": "An in-memory implementation of the artifact service.\n\nIt is not suitable for multi-threaded production environments. Use it for\ntesting and development only.",
   "type": "object",
   "properties": {
      "artifacts": {
         "additionalProperties": {
            "items": {
               "$ref": "#/$defs/_ArtifactEntry"
            },
            "type": "array"
         },
         "title": "Artifacts",
         "type": "object"
      }
   },
   "$defs": {
      "ArtifactVersion": {
         "description": "Metadata describing a specific version of an artifact.",
         "properties": {
            "version": {
               "description": "Monotonically increasing identifier for the artifact version.",
               "title": "Version",
               "type": "integer"
            },
            "canonicalUri": {
               "description": "Canonical URI referencing the persisted artifact payload.",
               "title": "Canonicaluri",
               "type": "string"
            },
            "customMetadata": {
               "additionalProperties": true,
               "description": "Optional user-supplied metadata stored with the artifact.",
               "title": "Custommetadata",
               "type": "object"
            },
            "createTime": {
               "description": "Unix timestamp (seconds) when the version record was created.",
               "title": "Createtime",
               "type": "number"
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
               "description": "MIME type when the artifact payload is stored as binary data.",
               "title": "Mimetype"
            }
         },
         "required": [
            "version",
            "canonicalUri"
         ],
         "title": "ArtifactVersion",
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
      },
      "_ArtifactEntry": {
         "properties": {
            "data": {
               "$ref": "#/$defs/Part"
            },
            "artifact_version": {
               "$ref": "#/$defs/ArtifactVersion"
            }
         },
         "required": [
            "data",
            "artifact_version"
         ],
         "title": "_ArtifactEntry",
         "type": "object"
      }
   }
}
```


**Fields:**
artifacts (dict[str, list[google.adk.artifacts.in_memory_artifact_service._ArtifactEntry]])


***field*artifacts*:**dict**[**str**,**list**[**_ArtifactEntry**]**]**[Optional]*¶**

***async*delete_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Deletes an artifact.


**Return type:**
None


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, delete the user-scoped artifact.


***async*get_artifact_version(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets the metadata for a specific version of an artifact.


**Return type:**
Optional[ArtifactVersion]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, the artifact will be fetched from the user-scoped artifacts. Otherwise, it will be fetched from the specified session.

**version**– The version number of the artifact to retrieve. IfNone, the latest version will be returned.


**Returns:**
An ArtifactVersion object containing the metadata of the specified artifact version, orNoneif the artifact version is not found.


***async*list_artifact_keys(***,*app_name*,*user_id*,*session_id**=**None*)¶**
Lists all the artifact filenames within a session.


**Return type:**
list[str]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**session_id**– The ID of the session.


**Returns:**
A list of artifact filenames. Ifsession_idis provided, returns both session-scoped and user-scoped artifact filenames. Ifsession_idisNone, returns user-scoped artifact filenames.


***async*list_artifact_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions and their metadata for a specific artifact.


**Return type:**
list[ArtifactVersion]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, lists versions of the user-scoped artifact. Otherwise, lists versions of the artifact within the specified session.


**Returns:**
A list of ArtifactVersion objects, each representing a version of the artifact and its associated metadata.


***async*list_versions(***,*app_name*,*user_id*,*filename*,*session_id**=**None*)¶**
Lists all versions of an artifact.


**Return type:**
list[int]


**Parameters:**
**app_name**– The name of the application.

**user_id**– The ID of the user.

**filename**– The name of the artifact file.

**session_id**– The ID of the session. IfNone, only list the user-scoped artifacts versions.


**Returns:**
A list of all available versions of the artifact.


***async*load_artifact(***,*app_name*,*user_id*,*filename*,*session_id**=**None*,*version**=**None*)¶**
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.


**Return type:**
Optional[Part]


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**session_id**– The session ID. IfNone, load the user-scoped artifact.

**version**– The version of the artifact. If None, the latest version will be returned.


**Returns:**
The artifact or None if not found.


***async*save_artifact(***,*app_name*,*user_id*,*filename*,*artifact*,*session_id**=**None*,*custom_metadata**=**None*)¶**
Saves an artifact to the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename. After saving the artifact, a revision ID is returned to identify the artifact version.


**Return type:**
int


**Parameters:**
**app_name**– The app name.

**user_id**– The user ID.

**filename**– The filename of the artifact.

**artifact**– The artifact to save. If the artifact consists offile_data, the artifact service assumes its content has been uploaded separately, and this method will associate thefile_datawith the artifact if necessary.

**session_id**– The session ID. IfNone, the artifact is user-scoped.

**custom_metadata**– custom metadata to associate with the artifact.


**Returns:**
The revision ID. The first version of the artifact has a revision ID of 0. This is incremented by 1 after each successful save.