Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.agents

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