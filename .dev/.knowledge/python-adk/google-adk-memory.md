# google.adk.memory module¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.memory

***class*google.adk.memory.BaseMemoryService¶**
Bases:ABC

Base class for memory services.

The service provides functionalities to ingest sessions into memory so that the memory can be used for user queries.


***abstractmethod**async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***abstractmethod**async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query.


**Return type:**
SearchMemoryResponse


**Parameters:**
**app_name**– The name of the application.

**user_id**– The id of the user.

**query**– The query to search for.


**Returns:**
A SearchMemoryResponse containing the matching memories.


***class*google.adk.memory.InMemoryMemoryService¶**
Bases:[BaseMemoryService

An in-memory memory service for prototyping purpose only.

Uses keyword matching instead of semantic search.

This class is thread-safe, however, it should be used for testing and development only.


***async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query.


**Return type:**
SearchMemoryResponse


**Parameters:**
**app_name**– The name of the application.

**user_id**– The id of the user.

**query**– The query to search for.


**Returns:**
A SearchMemoryResponse containing the matching memories.


***class*google.adk.memory.VertexAiMemoryBankService(*project**=**None*,*location**=**None*,*agent_engine_id**=**None*,***,*express_mode_api_key**=**None*)¶**
Bases:[BaseMemoryService

Implementation of the BaseMemoryService using Vertex AI Memory Bank.

Initializes a VertexAiMemoryBankService.


**Parameters:**
**project**– The project ID of the Memory Bank to use.

**location**– The location of the Memory Bank to use.

**agent_engine_id**– The ID of the agent engine to use for the Memory Bank, e.g. ‘456’ in ‘projects/my-project/locations/us-central1/reasoningEngines/456’. To extract from api_resource.name, use:agent_engine.api_resource.name.split('/')[-1]

**express_mode_api_key**– The API key to use for Express Mode. If not provided, the API key from the GOOGLE_API_KEY environment variable will be used. It will only be used if GOOGLE_GENAI_USE_VERTEXAI is true. Do not use Google AI Studio API key for this field. For more details, visit[https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview


***async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query.


**Parameters:**
**app_name**– The name of the application.

**user_id**– The id of the user.

**query**– The query to search for.


**Returns:**
A SearchMemoryResponse containing the matching memories.


***class*google.adk.memory.VertexAiRagMemoryService(*rag_corpus**=**None*,*similarity_top_k**=**None*,*vector_distance_threshold**=**10*)¶**
Bases:[BaseMemoryService

A memory service that uses Vertex AI RAG for storage and retrieval.

Initializes a VertexAiRagMemoryService.


**Parameters:**
**rag_corpus**– The name of the Vertex AI RAG corpus to use. Format:projects/{project}/locations/{location}/ragCorpora/{rag_corpus_id}or{rag_corpus_id}

**similarity_top_k**– The number of contexts to retrieve.

**vector_distance_threshold**– Only returns contexts with vector distance smaller than the threshold.


***async*add_session_to_memory(*session*)¶**
Adds a session to the memory service.

A session may be added multiple times during its lifetime.


**Parameters:**
**session**– The session to add.


***async*search_memory(***,*app_name*,*user_id*,*query*)¶**
Searches for sessions that match the query using rag.retrieval_query.


**Return type:**
SearchMemoryResponse