# ADK Command Line Interface Documentation

Source: https://google.github.io/adk-docs/runtime/command-line/

## Overview

The Agent Development Kit provides an interactive terminal interface for testing agents. This feature is supported across multiple languages: Python v0.1.0, TypeScript v0.2.0, Go v0.1.0, and Java v0.1.0.

## Running an Agent

### Basic Command

Different languages have distinct execution methods:

- **Python**: `adk run my_agent`
- **TypeScript**: `npx @google/adk-devtools run agent.ts`
- **Go**: `go run agent.go`
- **Java**: Create an `AgentCliRunner` class and execute via `mvn compile exec:java -Dexec.mainClass="com.example.agent.AgentCliRunner"`

### Interactive Session Example

Once launched, users receive an interactive prompt where they can "type queries and see agent responses directly in your terminal."

Example interaction:
```
[user]: What's the weather in New York?
[my_agent]: The weather in New York is sunny with a temperature of 25°C.
[user]: exit
```

## Session Management

### Saving Sessions

Use `--save_session` to preserve conversations upon exit. Users can either provide a session ID upfront or be prompted to enter one:

```
adk run --save_session --session_id my_session path/to/my_agent
```

Sessions are saved as JSON files following the pattern `<session_id>.session.json`.

### Resuming Sessions

Load previous conversations with:
```
adk run --resume path/to/my_agent/my_session.session.json path/to/my_agent
```

This "loads the previous session state and event history, displays it, and allows you to continue the conversation."

### Replaying Sessions

Execute non-interactive playback using:
```
adk run --replay path/to/input.json path/to/my_agent
```

Input files require this structure:
```json
{
  "state": {"key": "value"},
  "queries": ["Question 1", "Question 2"]
}
```

## Storage Configuration

| Option | Purpose | Default |
|--------|---------|---------|
| `--session_service_uri` | Custom session storage location | SQLite under `.adk/session.db` |
| `--artifact_service_uri` | Custom artifact storage location | Local `.adk/artifacts` |

### Storage Example

```
adk run --session_service_uri "sqlite:///my_sessions.db" path/to/my_agent
```

## Complete Option Reference

- `--save_session`: Persist conversation to JSON on exit
- `--session_id`: Specify session identifier when saving
- `--resume`: Path to saved session file for continuation
- `--replay`: Path to input file for automated playback
- `--session_service_uri`: Custom session storage URI
- `--artifact_service_uri`: Custom artifact storage URI
