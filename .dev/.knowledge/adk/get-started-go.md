# Go Quickstart for ADK - Content Summary

Source: https://google.github.io/adk-docs/get-started/go/

## Overview
This page provides a guide for getting started with the Agent Development Kit (ADK) for Go, covering project setup, agent creation, and execution methods.

## Prerequisites
- Go 1.24.4 or later
- ADK Go v0.2.0 or later

## Project Structure
The guide instructs users to create a basic directory with:
- `agent.go` - main agent code
- `.env` - API keys and project IDs

## Key Code Components
The sample agent demonstrates:
- Creating a Gemini model instance with API authentication
- Building an LLM agent named "hello_time_agent" with Google Search capability
- Configuring a launcher to execute the agent

The code imports essential packages including the ADK agent framework, Gemini model support, and launcher utilities.

## Execution Methods
**Command-line interface**: Run via `go run agent.go` after loading environment variables

**Web interface**: Start with `go run agent.go web api webui` to access a chat interface at localhost:8080

## Important Notes
- Users must load environment variables before execution (via `.env` or `env.bat`)
- ADK Web is "not meant for use in production deployments" and serves development purposes only
- The guide references support for multiple AI models beyond Gemini

## Related Resources
- Links to Python and TypeScript quickstarts
- Connection to broader build guides and model configuration documentation
- API reference materials for Go ADK
