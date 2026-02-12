# User Simulation in ADK Evaluation

Source: https://google.github.io/adk-docs/evaluate/

## Overview

"When evaluating conversational agents, it is not always practical to use a fixed set of user prompts, as the conversation can proceed in unexpected ways." ADK enables dynamic user prompt generation via AI models to address this challenge in agent evaluation.

## Core Concept: Conversation Scenarios

Conversation scenarios guide agent evaluation through two key components:

- **starting_prompt**: A fixed initial user message
- **conversation_plan**: Guidelines for subsequent interactions that an LLM uses to dynamically generate prompts based on conversation history

### Example Scenario Structure

```json
{
  "starting_prompt": "What can you do for me?",
  "conversation_plan": "Ask the agent to roll a 20-sided die. After you get the result, ask the agent to check if it is prime."
}
```

## Implementation Steps

### 1. Create Conversation Scenarios File
Save multiple scenarios defining user goals and conversation flow patterns in JSON format.

### 2. Create Session Input File
Define app configuration:
```json
{
  "app_name": "hello_world",
  "user_id": "user"
}
```

### 3. Add Scenarios to EvalSet
```bash
adk eval_set create [path] [eval_set_name]
adk eval_set add_eval_case [path] [eval_set_name] \
  --scenarios_file [scenarios_file] \
  --session_input_file [session_input_file]
```

### 4. Configure Evaluation Metrics
Create `EvalConfig` specifying evaluation criteria suitable for dynamic conversations (e.g., hallucinations, safety metrics that don't require predetermined responses).

### 5. Run Evaluation
```bash
adk eval [path] --config_file_path [config_file] \
  [eval_set_name] --print_detailed_results
```

## User Simulator Configuration

Customize behavior via `user_simulator_config` in EvalConfig:

```json
{
  "user_simulator_config": {
    "model": "gemini-2.5-flash",
    "model_configuration": {
      "thinking_config": {
        "include_thoughts": true,
        "thinking_budget": 10240
      }
    },
    "max_allowed_invocations": 20,
    "custom_instructions": "[optional]"
  }
}
```

**Key Parameters:**
- `model`: LLM powering the simulator
- `model_configuration`: Controls model behavior (thinking, temperature, etc.)
- `max_allowed_invocations`: Maximum conversation turns before termination
- `custom_instructions`: Optional override using placeholders like `{conversation_plan}`, `{conversation_history}`, `{stop_signal}`

## Requirements

- ADK Python v1.18.0 or later
- Interactive Colab notebook available for hands-on testing
