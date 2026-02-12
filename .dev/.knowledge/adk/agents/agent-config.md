# Agent Config - Agent Development Kit

**Source:** https://google.github.io/adk-docs/agents/config/
**Downloaded:** 2026-02-11

## Overview
Agent Config is an experimental feature in ADK Python v1.11.0 that enables building agents using YAML files without coding. Users can assemble complex agents incorporating functions, tools, and sub-agents through declarative configuration.

## Basic Structure
A minimal Agent Config example:
```yaml
name: assistant_agent
model: gemini-2.5-flash
description: A helper agent that can answer users' questions.
instruction: You are an agent to help answer users' various questions.
```

## Setup Requirements

**Installation & Prerequisites:**
- Install ADK Python libraries via standard installation instructions
- Verify installation: `adk --version`
- Ensure Python environment is active (use `source .venv/bin/activate` on Mac/Linux)

**Model Access Configuration:**
Create a `.env` file with credentials:
- Google API: `GOOGLE_API_KEY=<your-key>`
- Vertex AI: `GOOGLE_GENAI_USE_VERTEXAI=1` with GCP project/location settings

## Project Creation & Configuration

**Create project:**
```
adk create --type=config my_agent
```

This generates a folder containing `root_agent.yaml` and `.env` file.

**Edit root_agent.yaml** with agent definition, tools, instructions, and sub-agent references.

## Running Agents

Three execution modes available:
- `adk web` — web interface
- `adk run` — terminal execution
- `adk api_server` — service deployment

## Configuration Examples

**Built-in Tools:** Google Search integration
```yaml
tools:
  - name: google_search
```

**Custom Tools:** Python-based functionality referencing external modules

**Sub-agents:** Delegation architecture via `sub_agents:` section with YAML references

## Supported Tools
- google_search
- load_artifacts
- url_context
- exit_loop
- preload_memory
- get_user_choice
- enterprise_web_search
- load_web_page

## Known Limitations

- **Models:** Only Gemini supported
- **Languages:** Python only
- **Agent Types:** LangGraphAgent and A2aAgent unsupported
- **Tools:** Not all ADK tools fully supported; some require fully-qualified paths

## Deployment
Agents deploy via Cloud Run and Agent Engine using standard procedures for code-based agents.
