# google.adk.tools.agent_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.agent_tool)

---


google.adk.tools.agent_tool module


class google.adk.tools.agent_tool.AgentTool(agent, skip_summarization=False, *, include_plugins=True)
Bases: BaseTool
A tool that wraps an agent.
This tool allows an agent to be called as a tool within a larger application.
The agent’s input schema is used to define the tool’s input parameters, and
the agent’s output is returned as the tool’s result.


agent
The agent to wrap.




skip_summarization
Whether to skip summarization of the agent output.




include_plugins
Whether to propagate plugins from the parent runner context
to the agent’s runner. When True (default), the agent will inherit all
plugins from its parent. Set to False to run the agent with an isolated
plugin environment.




classmethod from_config(config, config_abs_path)
Creates a tool instance from a config.
This default implementation uses inspect to automatically map config values
to constructor arguments based on their type hints. Subclasses should
override this method for custom initialization logic.

Return type:
AgentTool

Parameters:

config – The config for the tool.
config_abs_path – The absolute path to the config file that contains the
tool config.


Returns:
The tool instance.






populate_name()

Return type:
Any






async run_async(*, args, tool_context)
Runs the tool with the given arguments and context.

Return type:
Any



Note

Required if this tool needs to run at the client side.
Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for
Gemini.



Parameters:

args – The LLM-filled arguments.
tool_context – The context of the tool.


Returns:
The result of running the tool.








pydantic model google.adk.tools.agent_tool.AgentToolConfig
Bases: BaseToolConfig
The config for the AgentTool.

Show JSON schema{
   "title": "AgentToolConfig",
   "description": "The config for the AgentTool.",
   "type": "object",
   "properties": {
      "agent": {
         "$ref": "#/$defs/AgentRefConfig"
      },
      "skip_summarization": {
         "default": false,
         "title": "Skip Summarization",
         "type": "boolean"
      },
      "include_plugins": {
         "default": true,
         "title": "Include Plugins",
         "type": "boolean"
      }
   },
   "$defs": {
      "AgentRefConfig": {
         "additionalProperties": false,
         "description": "The config for the reference to another agent.",
         "properties": {
            "config_path": {
               "anyOf": [
                  {
                     "type": "string"
                  },
                  {
                     "type": "null"
                  }
               ],
               "default": null,
               "title": "Config Path"
            },
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
               "title": "Code"
            }
         },
         "title": "AgentRefConfig",
         "type": "object"
      }
   },
   "additionalProperties": false,
   "required": [
      "agent"
   ]
}



Fields:

agent (google.adk.agents.common_configs.AgentRefConfig)
include_plugins (bool)
skip_summarization (bool)





field agent: AgentRefConfig [Required]
The reference to the agent instance.




field include_plugins: bool = True
Whether to include plugins from parent runner context.




field skip_summarization: bool = False
Whether to skip summarization of the agent output.





