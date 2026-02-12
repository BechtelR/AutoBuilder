# Session: Tracking Individual Conversations

## Overview

The `Session` object manages individual conversation threads within the Agent Development Kit. It serves as a container holding all interactions, context, and state for one specific chat thread.

## The Session Object

Key properties of a Session include:

**Identification**
- `id`: Unique identifier for the specific conversation thread
- `app_name`: Identifies which agent application owns this conversation
- `userId`: Links the conversation to a particular user

**History & State**
- `events`: Chronological sequence of all interactions (user messages, agent responses, tool actions)
- `state`: Temporary data storage relevant only to this ongoing conversation

**Activity Tracking**
- `lastUpdateTime`: Timestamp of the last event in this conversation thread

## Managing Sessions with SessionService

The `SessionService` acts as the central manager handling the complete lifecycle of conversation sessions. Core responsibilities include:

- Creating fresh Session objects for new interactions
- Retrieving existing sessions to resume conversations
- Appending new interactions to session history
- Listing active session threads for users and applications
- Deleting sessions when conversations conclude

## SessionService Implementations

### InMemorySessionService

"Stores all session data directly in the application's memory" with no persistence. Data is lost on application restart. Ideal for development, local testing, and scenarios not requiring long-term persistence.

### VertexAiSessionService

Uses Google Cloud Vertex AI infrastructure for persistent, scalable session management. Requires a Google Cloud project, storage bucket, and Reasoning Engine resource. Best for production applications on Google Cloud.

### DatabaseSessionService

Connects to relational databases (PostgreSQL, MySQL, SQLite) for persistent storage. Data survives application restarts. Suitable for applications managing their own database infrastructure.

## Session Lifecycle

The typical conversation cycle follows these steps:

1. Create or resume a session via SessionService
2. Runner retrieves the Session, providing agent access to state and events
3. Agent processes user query, potentially referencing session history
4. Agent generates response; Runner packages it as an Event
5. Runner calls `sessionService.append_event()` to save interaction and update state
6. Updated Session remains stored, ready for the next turn
7. Application calls `sessionService.delete_session()` when conversation ends

This cycle ensures conversational continuity by maintaining history and state for each session.

---

**Source**: https://google.github.io/adk-docs/sessions/session/
**Downloaded**: 2026-02-11
