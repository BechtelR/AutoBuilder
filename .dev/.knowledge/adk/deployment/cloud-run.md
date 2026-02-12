# Cloud Run Deployment Guide for Agent Development Kit

Source: https://google.github.io/adk-docs/deploy/cloud-run/

## Overview

Cloud Run enables deployment of ADK agents on Google's managed serverless platform. The documentation covers deployment methods for Python, Go, and Java agents.

## Key Deployment Methods

### Python Deployment Options

**ADK CLI (Recommended)**
The `adk deploy cloud_run` command automates deployment. Basic usage:

```bash
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  $AGENT_PATH
```

**gcloud CLI with Dockerfile**
Alternative manual approach using FastAPI integration. Requires creating `main.py`, `requirements.txt`, and `Dockerfile`.

### Go Deployment

The `adkgo deploy cloudrun` command (from adk-go repository) compiles and deploys agents. Key requirement: main.go must use the launcher framework to parse command-line arguments for web, api, and a2a services.

### Java Deployment

Uses `gcloud run deploy` with a multi-stage Dockerfile. Agents must be defined as "public static final BaseAgent ROOT_AGENT" variables.

## Prerequisites

- Google Cloud project with proper authentication (`gcloud auth login`)
- Environment variables configured for project and location
- Service account with secret access permissions
- API key stored in Google Cloud Secret Manager

## Required Agent Configuration

**Python**: Agent code in `agent.py`, variable named `root_agent`, with `__init__.py` and `requirements.txt`

**Go**: Main application in single file (typically main.go), agent passed to launcher configuration

**Java**: Agent in `CapitalAgent.java` as global public static final variable

## Deployment Payload Contents

The deployment uploads agent code, dependencies, and ADK API server code. The web UI is excluded by default unless specified via `--with_ui` flag or configuration settings.

## Testing Deployed Agents

**UI Testing**: Access the service URL in browser if UI enabled

**API Testing**: Use curl with endpoints:
- `GET /list-apps` - verify deployed applications
- `POST /apps/{app_name}/users/{user_id}/sessions/{session_id}` - create sessions
- `POST /run_sse` - execute agent with optional streaming

Authentication via identity token required if service deployed with authentication enabled.

## Key Configuration Elements

Environment variables needed:
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_API_KEY` or `GOOGLE_GENAI_USE_VERTEXAI=True`

Optional deployment flags include port specification, UI inclusion, temporary folder location, and gcloud pass-through arguments using `--` separator syntax.
