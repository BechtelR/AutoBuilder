# OpenAPI Tools - Agent Development Kit Documentation

## Overview

The Agent Development Kit (ADK) enables seamless integration of REST APIs through automatic tool generation from OpenAPI Specifications (v3.x). This eliminates manual definition of individual function tools for each API endpoint.

## Key Components

**OpenAPIToolset**: The primary class that parses OpenAPI specifications and generates callable tools automatically.

**RestApiTool**: Represents individual API operations (GET /pets/{petId}, POST /pets, etc.) created by OpenAPIToolset for each operation in the spec.

## How It Works

The process involves five main steps:

1. **Initialization & Parsing**: You provide the OpenAPI spec to OpenAPIToolset as a Python dictionary, JSON string, or YAML string. The toolset parses the spec and resolves internal references.

2. **Operation Discovery**: The system identifies all valid API operations within the specification's paths object.

3. **Tool Generation**: For each operation, OpenAPIToolset creates a RestApiTool instance with:
   - **Name**: Derived from the operationId (converted to snake_case, max 60 chars)
   - **Description**: Uses the operation's summary or description
   - **API Details**: HTTP method, path, server URL, parameters, and request body schema

4. **RestApiTool Functionality**: Each tool dynamically creates a FunctionDeclaration schema, executes HTTP requests using the LLM's arguments, and handles authentication and response handling.

5. **Authentication**: Global authentication (API keys, OAuth) configured during initialization applies automatically to all RestApiTools.

## Usage Workflow

Follow these steps:

1. Obtain your OpenAPI specification document
2. Instantiate OpenAPIToolset with the spec content and type
3. Add the toolset to your LlmAgent's tools list
4. Update agent instructions to reference the available API tools
5. Execute your agent using the Runner

## Code Example

```python
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.agents import LlmAgent

# Create toolset from OpenAPI spec
petstore_toolset = OpenAPIToolset(
    spec_str=openapi_spec_string,
    spec_str_type='json'
)

# Add to agent
root_agent = LlmAgent(
    name="petstore_manager_agent",
    model="gemini-2.0-flash",
    tools=[petstore_toolset],
    instruction="You are a Pet Store assistant managing pets via an API."
)
```

## Key Features

- Automatic schema generation from OpenAPI specs
- Support for path, query, header, and cookie parameters
- Request body handling for POST/PUT operations
- Built-in HTTP request execution
- Authentication configuration support
- Response handling returning JSON data to agents

The documentation includes a complete Pet Store API example using httpbin.org as a mock server, demonstrating listPets, createPet, and showPetById operations.

---

*Source: https://google.github.io/adk-docs/tools-custom/openapi-tools/*
*Downloaded: 2026-02-11*
