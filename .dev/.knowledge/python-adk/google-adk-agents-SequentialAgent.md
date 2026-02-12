Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.agents

***pydantic**model*google.adk.agents.SequentialAgent¶**
Bases:[BaseAgent

A shell agent that runs its sub-agents in sequence.


```
Show JSON schema{
   "title": "SequentialAgent",
   "description": "A shell agent that runs its sub-agents in sequence.",
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
alias ofSequentialAgentConfig


# google.adk.artifacts module¶

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