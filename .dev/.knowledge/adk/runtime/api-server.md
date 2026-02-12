# ADK API Server Documentation

Source: https://google.github.io/adk-docs/runtime/api-server/

## Overview

The API Server is a feature that allows developers to expose their agents through a REST API for programmatic testing and integration before deployment. It's supported across Python v0.1.0, TypeScript v0.2.0, Go v0.1.0, and Java v0.1.0.

## Starting the API Server

### Command Syntax by Language

**Python:**
```
adk api_server
```

**TypeScript:**
```
npx adk api_server
```

**Go:**
```
go run agent.go web api
```

**Java (Maven):**
```
mvn compile exec:java \
 -Dexec.args="--adk.agents.source-dir=src/main/java/agents --server.port=8080"
```

**Java (Gradle):**
Create a task in `build.gradle` or `build.gradle.kts`, then run:
```
gradle runADKWebServer
```

The server runs on `http://localhost:8000` by default.

## Local Testing Workflow

### 1. Create a Session

```bash
curl -X POST http://localhost:8000/apps/my_sample_agent/users/u_123/sessions/s_123 \
  -H "Content-Type: application/json" \
  -d '{"key1": "value1", "key2": 42}'
```

This returns session information with format: `{"id":"s_123","appName":"my_sample_agent","userId":"u_123","state":{...}}`

### 2. Send Queries

Two primary endpoints exist for query execution:

**`/run` - Single Response:**
Returns all events as a complete JSON array after execution completes.

```bash
curl -X POST http://localhost:8000/run \
-H "Content-Type: application/json" \
-d '{
"appName": "my_sample_agent",
"userId": "u_123",
"sessionId": "s_123",
"newMessage": {
    "role": "user",
    "parts": [{
    "text": "Hey whats the weather in new york today"
    }]
}
}'
```

**`/run_sse` - Server-Sent Events (Streaming):**
Returns events as a stream using Server-Sent Events format. Supports token-level streaming by setting `"streaming": true`.

```bash
curl -X POST http://localhost:8000/run_sse \
-H "Content-Type: application/json" \
-d '{
"appName": "my_sample_agent",
"userId": "u_123",
"sessionId": "s_123",
"newMessage": {
    "role": "user",
    "parts": [{
    "text": "Hey whats the weather in new york today"
    }]
},
"streaming": false
}'
```

### 3. Send Queries with File Attachments

Base64-encoded files can be included in requests:

```bash
curl -X POST http://localhost:8000/run \
-H 'Content-Type: application/json' \
-d '{
   "appName":"my_sample_agent",
   "userId":"u_123",
   "sessionId":"s_123",
   "newMessage":{
      "role":"user",
      "parts":[
         {
            "text":"Describe this image"
         },
         {
            "inlineData":{
               "displayName":"my_image.png",
               "data":"iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAACXBIWXMAAAsTAAALEwEAmpw...",
               "mimeType":"image/png"
            }
         }
      ]
   },
   "streaming":false
}'
```

## Key API Endpoints

### Utility Endpoints

**List Available Agents:**
- **Method:** GET
- **Path:** `/list-apps`
- **Response:** Array of agent names

### Session Management

**Update Session:**
- **Method:** PATCH
- **Path:** `/apps/{app_name}/users/{user_id}/sessions/{session_id}`
- **Body:** `{"stateDelta": {"key": "value"}}`

**Get Session:**
- **Method:** GET
- **Path:** `/apps/{app_name}/users/{user_id}/sessions/{session_id}`

**Delete Session:**
- **Method:** DELETE
- **Path:** `/apps/{app_name}/users/{user_id}/sessions/{session_id}`
- **Response:** 204 No Content status on success

## Interactive Documentation

Access Swagger UI documentation at `http://localhost:8000/docs` to explore endpoints and test requests interactively.

## Integration & Deployment

The documentation mentions "third-party observability tools" like Comet Opik integration through callbacks for tracing agent interactions. Deployment options include:

- **Agent Engine** - Managed service on Vertex AI
- **Cloud Run** - Serverless architecture on Google Cloud

## JSON Naming Convention

All request and response bodies use camelCase for field names (e.g., `appName`, `userId`, `sessionId`). TypeScript currently only supports camelCase formatting.
