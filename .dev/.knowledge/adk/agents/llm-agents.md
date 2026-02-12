# LLM Agents

Source: https://google.github.io/adk-docs/agents/llm-agents/

## Core Concept

The `LlmAgent` is a foundational component that leverages Large Language Models for reasoning, understanding natural language, making decisions, and generating responses. Unlike deterministic workflow agents, it exhibits non-deterministic behavior, dynamically deciding which tools to use and how to proceed based on instructions and context.

## Essential Configuration Components

### 1. Agent Identity (Required Parameters)

**Name**: A unique string identifier crucial for internal operations and multi-agent systems. Choose descriptive names reflecting function (e.g., `customer_support_router`).

**Model**: The underlying LLM powering the agent's reasoning. Examples include `gemini-2.5-flash`. Model selection impacts capabilities, cost, and performance.

**Description**: Optional but recommended for multi-agent setups. Concise summary helping other agents determine task routing. Should be specific about capabilities.

### 2. Instructions (Critical Parameter)

Instructions shape agent behavior through:
- Core task or goal definition
- Personality or persona establishment
- Behavioral constraints
- Tool usage guidance with context-specific explanations
- Desired output format specifications

**Key recommendations**: Be explicit and unambiguous. Use markdown for complex instructions. Include few-shot examples for specific formats. Explain *when* and *why* agents should use tools.

**Dynamic Content**: Instructions support template syntax using `{var}`, `{artifact.var}`, and optional `{var?}` syntax for graceful handling of missing values.

### 3. Tools (Capability Extension)

Tools extend agent capabilities through:
- Native functions (auto-wrapped in Python)
- BaseTool class instances
- AgentTool instances (for agent delegation)

The LLM uses function names, descriptions from docstrings, and parameter schemas to determine tool invocation based on conversation context.

## Advanced Configuration

### Fine-Tuning Generation (`generate_content_config`)

Controls LLM response generation through parameters like:
- `temperature`: Controls randomness (lower = more deterministic)
- `max_output_tokens`: Response length limits
- `top_p`, `top_k`: Sampling parameters
- Safety settings configuration

### Structured Data Management

**`input_schema`**: Defines expected input structure; user messages must conform to this schema if set.

**`output_schema`**: Enforces JSON output conforming to specified structure. *Note*: When output schemas are set, tools cannot be used.

**`output_key`**: Stores final response text in session state under specified key, enabling inter-agent data passing.

### Context Management (`include_contents`)

- `'default'`: Agent receives relevant conversation history
- `'none'`: Agent operates solely on current instruction and immediate input (stateless operations)

### Planning Capabilities

**BuiltInPlanner**: Leverages model's native planning features (e.g., Gemini thinking) with configurable thinking budget.

**PlanReActPlanner**: Structures output with explicit planning, action, reasoning, and final answer sections for models lacking built-in thinking features.

### Code Execution

`BaseCodeExecutor` instances enable agents to execute code blocks in responses, supporting languages like Python for calculations and data processing.

## Implementation Pattern

Effective agent development follows this sequence:
1. Define identity (name, model, description)
2. Create comprehensive instructions with examples
3. Equip with relevant tools
4. Apply advanced configurations based on use case
5. Test with various inputs

The platform supports implementation across Python, TypeScript, Go, and Java with consistent conceptual patterns across languages.
