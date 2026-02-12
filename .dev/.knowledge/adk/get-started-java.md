# Java Quickstart for ADK - Content Summary

Source: https://google.github.io/adk-docs/get-started/java/

## Overview
This guide enables developers to build agents using the Agent Development Kit (ADK) for Java, requiring Java 17+ and Maven 3.9+.

## Project Setup

### Directory Structure
```
my_agent/
    src/main/java/com/example/agent/
        HelloTimeAgent.java
        AgentCliRunner.java
    pom.xml
    .env
```

### Key Dependencies
The core requirement is: `"The ADK core dependency com.google.adk:google-adk version 0.3.0"`

Additional development dependency:
- google-adk-dev (version 0.3.0) - provides web UI debugging tools

## Sample Agent Implementation

The quickstart creates a `HelloTimeAgent` that:
- Uses the Gemini 2.5 Flash model
- Implements a `getCurrentTime()` function tool
- Provides city-based time information through a mock implementation

**Important Note:** ADK Java v0.3.0 and lower is incompatible with Gemini 3 Pro Preview due to function calling signature changes.

## Running the Agent

Two execution methods:
1. **Command-line interface:** Interactive terminal-based interaction
2. **Web interface:** Browser-based chat interface at localhost:8000

Both methods require loading environment variables (API keys) via `.env` file setup.

## Next Steps
The guide directs users to the [Build your Agent](/adk-docs/tutorials/) section for advanced development patterns.
