# Google Search Grounding - Agent Development Kit

## What You'll Learn

This guide covers:
- Quick setup for creating Google Search-enabled agents
- Grounding architecture and data flow
- Response structure and metadata interpretation
- Best practices for displaying search results with citations

## Google Search Grounding Quickstart

### 1. Environment Setup & ADK Installation

**Python:**
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install google-adk
```

**TypeScript:**
```bash
npm init -y
npm install @google/adk
```

### 2. Create Agent Project

Create directory structure and files:
```bash
mkdir google_search_agent
echo "from . import agent" > google_search_agent/__init__.py
touch google_search_agent/agent.py .env
```

#### Agent Code

**Python (agent.py):**
```python
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="google_search_agent",
    model="gemini-2.5-flash",
    instruction="Answer questions using Google Search when needed. Always cite sources.",
    description="Professional search assistant with Google Search capabilities",
    tools=[google_search]
)
```

**TypeScript (agent.ts):**
```typescript
import { LlmAgent, GOOGLE_SEARCH } from '@google/adk';

const rootAgent = new LlmAgent({
    name: "google_search_agent",
    model: "gemini-2.5-flash",
    instruction: "Answer questions using Google Search when needed. Always cite sources.",
    description: "Professional search assistant with Google Search capabilities",
    tools: [GOOGLE_SEARCH],
});
```

### 3. Platform Configuration

**Google AI Studio (.env):**
```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=YOUR_API_KEY
```

**Vertex AI (.env):**
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=LOCATION
```

### 4. Run Your Agent

**Web Interface:**
```bash
adk web
```

**Terminal:**
```bash
adk run google_search_agent
```

### Example Prompts

- What is the weather in New York?
- What is the time in Paris?
- What is the weather in Paris?

## How Grounding Works

### Data Flow

1. **User Query** → Agent receives user input
2. **ADK Orchestration** → Routes message through agent system
3. **LLM Analysis** → Model determines if web search is needed
4. **Grounding Service** → Executes Google Search queries
5. **Context Injection** → Results integrated into model context
6. **Response Generation** → Model creates grounded answer
7. **Attribution** → Sources and metadata provided to user

### Response Structure

The response includes:

- **groundingChunks**: Web pages consulted with titles and URIs
- **groundingSupports**: Connections between text segments and sources
- **segment**: Specific text portions with start/end indices
- **groundingChunkIndices**: References to supporting sources

Example:
```
"They defeated FC Porto 2-1 in their second group stage match."
→ Supported by groundingChunks[0] and groundingChunks[1]
```

### Search Suggestions Display

The `searchEntryPoint` in metadata contains pre-formatted HTML for displaying related query suggestions as clickable chips, enabling users to explore related topics.

## Summary

Google Search Grounding enables agents to:
- Access current information beyond training data
- Provide transparent source attribution
- Deliver fact-based answers with verification capability
- Enhance experience with relevant search suggestions

This transforms agents into dynamic, web-connected assistants providing real-time, accurate information with verifiable sources.

---

**Source**: https://google.github.io/adk-docs/grounding/google_search_grounding/
**Downloaded**: 2026-02-11
