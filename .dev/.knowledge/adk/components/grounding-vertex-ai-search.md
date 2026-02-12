# Vertex AI Search Grounding for Agent Development Kit

## Overview

Vertex AI Search Grounding enables ADK agents to access information from private enterprise documents and data repositories. This feature allows AI agents to provide answers grounded in an organization's knowledge base with proper source attribution.

## Key Learning Points

The documentation covers:
- Quick setup for creating Vertex AI Search-enabled agents
- Grounding architecture and data flow
- Response structure and metadata interpretation
- Best practices for displaying citations

## Quickstart Setup

### Prerequisites
- Python 3.10+ or Node.js
- Google Cloud Project with Vertex AI Search datastore
- gcloud CLI authentication

### Installation Steps

1. **Prepare Vertex AI Search**: Create a datastore with indexed documents and retrieve the Data Store ID

2. **Environment Setup**:
   - Create Python virtual environment or Node.js project
   - Install ADK: `pip install google-adk` or `npm install @google/adk`

3. **Create Agent**:
   ```python
   from google.adk.agents import Agent
   from google.adk.tools import VertexAiSearchTool

   root_agent = Agent(
       name="vertex_search_agent",
       model="gemini-2.5-flash",
       instruction="Answer questions using Vertex AI Search...",
       tools=[VertexAiSearchTool(data_store_id=DATASTORE_ID)]
   )
   ```

4. **Authentication**: Configure `.env` with Google Cloud credentials

5. **Run Agent**: Use `adk web` or `adk run` commands

## How It Works

The grounding process follows this flow:

1. User submits query to agent
2. LLM analyzes whether enterprise data is needed
3. VertexAiSearchTool queries the Vertex AI Search datastore
4. Relevant documents are retrieved and ranked
5. Retrieved content is injected into model context
6. LLM generates grounded response with source metadata
7. Response includes citations and document references

## Response Structure

Grounded responses include:
- **groundingChunks**: List of source documents consulted
- **groundingSupports**: Links between response text and sources
- **retrievalQueries**: Search queries executed against datastore

Each chunk contains document title, URI, and ID for verification.

## Citation Display

While citation display is optional, the metadata enables:
- Simple text output showing document count
- Enhanced interactive citations mapping statements to sources
- User access verification for referenced documents

The documentation emphasizes that grounding transforms agents into "enterprise-specific knowledge systems capable of providing accurate, source-attributed information."

---

**Source**: https://google.github.io/adk-docs/grounding/vertex_ai_search_grounding/
**Downloaded**: 2026-02-11
