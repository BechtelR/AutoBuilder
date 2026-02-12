# TypeScript Quickstart for Agent Development Kit

Source: https://google.github.io/adk-docs/get-started/typescript/

## Overview
This documentation page provides a guide for setting up and running an Agent Development Kit (ADK) agent using TypeScript.

## Prerequisites
- Node.js 24.13.0 or later
- npm 11.8.0 or later

## Project Setup Steps

### 1. Create Project Structure
Create a directory called `my-agent/` for the project.

### 2. Configure Dependencies
The guide instructs users to:
- Initialize the project as an ES module
- Set the main entry point to `agent.ts`
- Install the `@google/adk` library
- Install `@google/adk-devtools` as a development dependency

### 3. Agent Code Example
The documentation includes a sample agent implementation featuring:
- A `FunctionTool` called `getCurrentTime` that returns current time in specified cities
- An `LlmAgent` named `hello_time_agent` using the Gemini 2.5 Flash model
- Tool parameter validation using Zod schema validation

### 4. API Key Configuration
Users must obtain a Gemini API key from Google AI Studio and add it to a `.env` file.

## Running the Agent

**CLI Mode:** `npx adk run agent.ts`

**Web Interface:** `npx adk web` (accessible at localhost:8000)

The page notes that the web interface is "**_not meant for use in production deployments_**" and is development-only.

## Next Steps
The guide directs users to additional resources for building more complex agents, including multi-tool agents, agent teams, and streaming agents.
