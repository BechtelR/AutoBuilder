# ADK Web Interface Documentation

Source: https://google.github.io/adk-docs/runtime/web-interface/

## Overview
The ADK web interface enables interactive testing of agents directly in a browser during development. According to the documentation, it provides "a simple way to interactively develop and debug your agents."

⚠️ **Development Only**: The tool is explicitly "not meant for use in production deployments."

## Getting Started

### Launch Commands

**Python:**
```
adk web
```

**TypeScript:**
```
npx adk web
```

**Go:**
```
go run agent.go web api webui
```

**Java (Maven):**
```
mvn compile exec:java \
 -Dexec.args="--adk.agents.source-dir=src/main/java/agents --server.port=8080"
```

**Java (Gradle):** Add a custom task to your build file, then run `gradle runADKWebServer`

The server runs on `http://localhost:8000` by default.

## Key Features

- **Chat interface**: Send messages and view real-time responses
- **Session management**: Create and switch between sessions
- **State inspection**: View and modify session state during development
- **Event history**: Inspect all events generated during execution

## Configuration Options

| Option | Purpose | Default |
|--------|---------|---------|
| `--port` | Server port | `8000` |
| `--host` | Host binding address | `127.0.0.1` |
| `--session_service_uri` | Custom session storage | In-memory |
| `--artifact_service_uri` | Custom artifact storage | Local `.adk/artifacts` |
| `--reload/--no-reload` | Auto-reload on code changes | `true` |

### Example with Custom Settings
```
adk web --port 3000 --session_service_uri "sqlite:///sessions.db"
```

**Platform Support:** Python v0.1.0+, TypeScript v0.2.0+, Go v0.1.0+, Java v0.1.0+
