# Deploy to Vertex AI Agent Engine - Documentation Summary

Source: https://google.github.io/adk-docs/deploy/agent-engine/

## Overview

Google Cloud Vertex AI Agent Engine is described as "a set of modular services that help developers scale and govern agents in production." The platform enables deployment of Agent Development Kit (ADK) agents with managed infrastructure.

## Deployment Paths

The documentation outlines two distinct deployment approaches:

1. **Standard Deployment**: Recommended for users with existing Google Cloud projects who want controlled, step-by-step deployment. This path uses Cloud Console and the ADK CLI, suited for those experienced with Google Cloud configuration.

2. **Agent Starter Pack (ASP)**: An accelerated path for new projects and development/testing environments. It configures additional Google Cloud services to streamline initial setup.

## Deployment Payload

When deploying an ADK agent to Agent Engine, the following uploads occur:

- Your ADK agent code
- Declared dependencies in your project

**Notably excluded**: The deployment does not include the ADK API server or web UI libraries, as Agent Engine provides these components directly.

## Important Considerations

Agent Engine is a paid service with potential costs above the free tier. Users should consult the Agent Engine pricing documentation before proceeding with deployments.

## Supported Languages

The documentation indicates Python ADK support is currently featured for Agent Engine deployment.
