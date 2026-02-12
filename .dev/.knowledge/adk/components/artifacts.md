# Artifacts - Agent Development Kit

## Overview

Artifacts represent a mechanism for managing named, versioned binary data associated with user sessions or persisting across multiple sessions. They enable agents and tools to handle data beyond text, including files, images, audio, and other binary formats.

## What are Artifacts?

An artifact is binary data identified by a unique filename string within a specific scope. Each save operation with the same filename creates a new version. Artifacts use the standard `google.genai.types.Part` object for representation, with core data stored in an `inline_data` structure containing:

- `data`: Raw binary content as bytes
- `mime_type`: Data type indicator (e.g., "image/png", "application/pdf")

## Why Use Artifacts?

Artifacts serve several key purposes:

- **Non-textual Data Handling**: Store images, audio, video, PDFs, spreadsheets
- **Large Data Persistence**: Manage substantial blobs without cluttering session state
- **User File Management**: Enable file uploads and downloads
- **Binary Output Sharing**: Save agent-generated files (reports, images) for later access
- **Expensive Operation Caching**: Store results of computationally intensive processes

## Common Use Cases

- Generated reports or files (PDFs, CSVs, charts)
- User file uploads for analysis or processing
- Intermediate binary results from multi-step processes
- Persistent user-specific configuration data
- Cached generated content (logos, audio greetings)

## Core Concepts

### Artifact Service (BaseArtifactService)

The central component managing storage and retrieval logic. Concrete implementations provide:

- Save artifact functionality
- Load artifact retrieval
- Listing artifact filenames
- Artifact deletion
- Version listing

You provide a service instance when initializing the Runner, making it available through InvocationContext.

### Artifact Data Structure

Artifacts consistently use `google.genai.types.Part` objects with inline data containing bytes and MIME type information for proper interpretation during retrieval.

### Filename Identification

Filenames are simple strings identifying artifacts within their namespace. Best practice involves descriptive names with extensions (e.g., "monthly_report.pdf"), though MIME type governs actual data interpretation.

### Versioning

The artifact service automatically handles versioning. Each `save_artifact` call assigns an incrementing version number (starting from 0). Load operations default to the latest version unless a specific version number is provided.

### Namespacing (Session vs. User)

- **Session Scope** (default): Plain filenames like "report.pdf" are tied to app_name, user_id, and session_id
- **User Scope**: "user:" prefixed filenames like "user:profile.png" are accessible across any session for that user

## Interacting with Artifacts

Access artifact methods through `CallbackContext` and `ToolContext` objects. Prerequisites include configuring a `BaseArtifactService` when initializing the Runner.

### Saving Artifacts

Call `save_artifact(filename, artifact)` passing a filename and `types.Part` object. The method returns the assigned version number and generates artifact delta events.

### Loading Artifacts

Use `load_artifact(filename)` to retrieve the latest version or `load_artifact(filename, version=N)` for specific versions. Returns None if not found.

### Listing Artifacts

Call `list_artifacts()` to retrieve available filenames in the current scope.

## Available Implementations

### InMemoryArtifactService

**Storage**: Python dictionaries or Java HashMaps in application memory

**Features**:
- Requires no external setup
- Fast in-memory operations
- Data lost on application termination
- Ephemeral storage only

**Use Cases**: Development, testing, temporary demonstrations

### GcsArtifactService

**Storage**: Google Cloud Storage buckets for persistent artifact storage

**Features**:
- Persistent across restarts and deployments
- Leverages GCS scalability and durability
- Each version stored as distinct object
- Requires appropriate IAM permissions

**Use Cases**: Production environments, cross-instance sharing, long-term storage

## Best Practices

- Select InMemoryArtifactService for prototyping; use GcsArtifactService for production
- Employ descriptive filenames with relevant extensions
- Always specify accurate MIME types for correct data interpretation
- Understand versioning behavior; latest version loads by default
- Use "user:" prefix deliberately for cross-session data only
- Implement comprehensive error handling for service availability and storage exceptions
- Consider size implications, especially with GCS
- Establish cleanup strategies for persistent storage using lifecycle policies or administrative deletion functions
- Check service configuration before calling context methods to avoid ValueError exceptions

---

**Source**: https://google.github.io/adk-docs/artifacts/
**Downloaded**: 2026-02-11
