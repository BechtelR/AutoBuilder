# Models
> Base: https://google.github.io/adk-docs

- **LiteLLM** `/agents/models/litellm/` — provider-agnostic routing; any LiteLLM-supported model string
- **Google Gemini** `/agents/models/google-gemini/` — native integration; gemini-2.0-flash, gemini-2.5-pro
- **Anthropic Claude** `/agents/models/anthropic/` — Claude via LiteLLM; claude-sonnet-4-5, claude-opus-4
- **Vertex AI** `/agents/models/vertex/` — Google Cloud managed models
- **Ollama** `/agents/models/ollama/` — local model serving
- **vLLM** `/agents/models/vllm/` — high-throughput inference server
- **Apigee** `/agents/models/apigee/` — API gateway integration

## Key Classes
`LiteLlm` `BaseLlm`

## See Also
→ runtime.md: model configuration in RunConfig
