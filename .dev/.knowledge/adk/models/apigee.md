# Apigee AI Gateway for ADK Agents - Documentation Summary

## Overview

The Apigee AI Gateway integration enables ADK agents to leverage enterprise-grade AI governance capabilities. According to the documentation, "Apigee provides a powerful AI Gateway, transforming how you manage and govern your generative AI model traffic."

## Key Capabilities

The platform delivers several governance features:

- **Model Safety**: Implements security policies like Model Armor for threat protection
- **Traffic Governance**: Enforces rate limiting and token limiting to manage costs and prevent abuse
- **Performance**: Uses semantic caching and advanced model routing to improve response times
- **Monitoring & Visibility**: Provides granular monitoring, analysis, and auditing of AI requests

## Supported Versions

- Python ADK v1.18.0+
- Java v0.4.0+

## Current Limitations

The documentation notes: "The ApigeeLLM wrapper is currently designed for use with Vertex AI and the Gemini API (generateContent)." Expansion to additional models is planned.

## Implementation Pattern

Developers instantiate an `ApigeeLlm` wrapper object with three key parameters:

1. **model**: The Apigee route to the underlying model (e.g., "apigee/gemini-2.5-flash")
2. **proxy_url**: The deployed Apigee proxy URL including base path
3. **custom_headers**: Authentication/authorization headers like API keys

The configured wrapper then passes to an `LlmAgent` or other agent type, routing all API calls through Apigee policies before reaching the underlying AI model endpoint.

---

*Source: https://google.github.io/adk-docs/agents/models/apigee/*
*Downloaded: 2026-02-11*
