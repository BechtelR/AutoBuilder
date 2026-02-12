# google.adk.tools.transfer_to_agent_tool

**Source**: [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.tools.transfer_to_agent_tool)

---


google.adk.tools.transfer_to_agent_tool module


class google.adk.tools.transfer_to_agent_tool.TransferToAgentTool(agent_names)
Bases: FunctionTool
A specialized FunctionTool for agent transfer with enum constraints.
This tool enhances the base transfer_to_agent function by adding JSON Schema
enum constraints to the agent_name parameter. This prevents LLMs from
hallucinating invalid agent names by restricting choices to only valid agents.


agent_names
List of valid agent names that can be transferred to.


Initialize the TransferToAgentTool.

Parameters:
agent_names – List of valid agent names that can be transferred to.






google.adk.tools.transfer_to_agent_tool.transfer_to_agent(agent_name, tool_context)
Transfer the question to another agent.
This tool hands off control to another agent when it’s more suitable to
answer the user’s question according to the agent’s description.

Return type:
None



Note
For most use cases, you should use TransferToAgentTool instead of this
function directly. TransferToAgentTool provides additional enum constraints
that prevent LLMs from hallucinating invalid agent names.


Parameters:
agent_name – the agent name to transfer to.





