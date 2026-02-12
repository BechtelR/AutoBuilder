# google.adk.apps package¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.apps

***pydantic**model*google.adk.apps.App¶**
Bases:BaseModel

Represents an LLM-backed agentic application.

AnAppis the top-level container for an agentic system powered by LLMs. It manages a root agent (root_agent), which serves as the root of an agent tree, enabling coordination and communication across all agents in the hierarchy. Thepluginsare application-wide components that provide shared capabilities and services to the entire system.


```
Show JSON schema{
   "title": "App",
   "type": "object",
   "properties": {
      "name": {
         "title": "Name",
         "type": "string"
      },
      "root_agent": {
         "$ref": "#/$defs/BaseAgent"
      },
      "plugins": {
         "default": null,
         "title": "Plugins"
      },
      "events_compaction_config": {
         "default": null,
         "title": "Events Compaction Config"
      },
      "context_cache_config": {
         "anyOf": [
            {
               "$ref": "#/$defs/ContextCacheConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
      },
      "resumability_config": {
         "anyOf": [
            {
               "$ref": "#/$defs/ResumabilityConfig"
            },
            {
               "type": "null"
            }
         ],
         "default": null
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
      "ContextCacheConfig": {
         "additionalProperties": false,
         "description": "Configuration for context caching across all agents in an app.\n\nThis configuration enables and controls context caching behavior for\nall LLM agents in an app. When this config is present on an app, context\ncaching is enabled for all agents. When absent (None), context caching\nis disabled.\n\nContext caching can significantly reduce costs and improve response times\nby reusing previously processed context across multiple requests.\n\nAttributes:\n    cache_intervals: Maximum number of invocations to reuse the same cache before refreshing it\n    ttl_seconds: Time-to-live for cache in seconds\n    min_tokens: Minimum tokens required to enable caching",
         "properties": {
            "cache_intervals": {
               "default": 10,
               "description": "Maximum number of invocations to reuse the same cache before refreshing it",
               "maximum": 100,
               "minimum": 1,
               "title": "Cache Intervals",
               "type": "integer"
            },
            "ttl_seconds": {
               "default": 1800,
               "description": "Time-to-live for cache in seconds",
               "exclusiveMinimum": 0,
               "title": "Ttl Seconds",
               "type": "integer"
            },
            "min_tokens": {
               "default": 0,
               "description": "Minimum estimated request tokens required to enable caching. This compares against the estimated total tokens of the request (system instruction + tools + contents). Context cache storage may have cost. Set higher to avoid caching small requests where overhead may exceed benefits.",
               "minimum": 0,
               "title": "Min Tokens",
               "type": "integer"
            }
         },
         "title": "ContextCacheConfig",
         "type": "object"
      },
      "ResumabilityConfig": {
         "description": "The config of the resumability for an application.\n\nThe \"resumability\" in ADK refers to the ability to:\n1. pause an invocation upon a long-running function call.\n2. resume an invocation from the last event, if it's paused or failed midway\nthrough.\n\nNote: ADK resumes the invocation in a best-effort manner:\n1. Tool call to resume needs to be idempotent because we only guarantee\nan at-least-once behavior once resumed.\n2. Any temporary / in-memory state will be lost upon resumption.",
         "properties": {
            "is_resumable": {
               "default": false,
               "title": "Is Resumable",
               "type": "boolean"
            }
         },
         "title": "ResumabilityConfig",
         "type": "object"
      }
   },
   "additionalProperties": false,
   "required": [
      "name",
      "root_agent"
   ]
}
```


**Fields:**
context_cache_config (google.adk.agents.context_cache_config.ContextCacheConfig | None)

events_compaction_config (google.adk.apps.app.EventsCompactionConfig | None)

name (str)

plugins (list[google.adk.plugins.base_plugin.BasePlugin])

resumability_config (google.adk.apps.app.ResumabilityConfig | None)

root_agent (google.adk.agents.base_agent.BaseAgent)


**Validators:**
_validate_name»all fields


***field*context_cache_config*:**ContextCacheConfig**|**None**=**None*¶**
Context cache configuration that applies to all LLM agents in the app.


**Validated by:**
_validate_name


***field*events_compaction_config*:**EventsCompactionConfig**|**None**=**None*¶**
The config of event compaction for the application.


**Validated by:**
_validate_name


***field*name*:**str**[Required]*¶**
The name of the application.


**Validated by:**
_validate_name


***field*plugins*:**list**[*[*BasePlugin**]**[Optional]*¶**
The plugins in the application.


**Validated by:**
_validate_name


***field*resumability_config*:*[*ResumabilityConfig**|**None**=**None*¶**
The config of the resumability for the application. If configured, will be applied to all agents in the app.


**Validated by:**
_validate_name


***field*root_agent*:*[*BaseAgent**[Required]*¶**
The root agent in the application. One app can only have one root agent.


**Validated by:**
_validate_name


***pydantic**model*google.adk.apps.ResumabilityConfig¶**
Bases:BaseModel

The config of the resumability for an application.

The “resumability” in ADK refers to the ability to: 1. pause an invocation upon a long-running function call. 2. resume an invocation from the last event, if it’s paused or failed midway through.

Note: ADK resumes the invocation in a best-effort manner: 1. Tool call to resume needs to be idempotent because we only guarantee an at-least-once behavior once resumed. 2. Any temporary / in-memory state will be lost upon resumption.


```
Show JSON schema{
   "title": "ResumabilityConfig",
   "description": "The config of the resumability for an application.\n\nThe \"resumability\" in ADK refers to the ability to:\n1. pause an invocation upon a long-running function call.\n2. resume an invocation from the last event, if it's paused or failed midway\nthrough.\n\nNote: ADK resumes the invocation in a best-effort manner:\n1. Tool call to resume needs to be idempotent because we only guarantee\nan at-least-once behavior once resumed.\n2. Any temporary / in-memory state will be lost upon resumption.",
   "type": "object",
   "properties": {
      "is_resumable": {
         "default": false,
         "title": "Is Resumable",
         "type": "boolean"
      }
   }
}
```


**Fields:**
is_resumable (bool)


***field*is_resumable*:**bool**=**False*¶**
Whether the app supports agent resumption. If enabled, the feature will be enabled for all agents in the app.