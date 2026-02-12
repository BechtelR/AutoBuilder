# google.adk.tools.google_search_tool - Detailed Documentation

## Module Overview

The `google_search` tool enables agents to perform web searches using Google Search. This tool integrates Google Search capabilities directly into ADK agents.

**Module:** `google.adk.tools.google_search_tool`
**Primary Class:** `GoogleSearchTool`
**Availability:** Python ADK v0.1.0+, TypeScript v0.2.0+, Go v0.1.0+, Java v0.2.0+

## Key Requirements

### Model Compatibility

**IMPORTANT:** The `google_search` tool is only compatible with Gemini 2 models.

Supported models:
- `gemini-2.0-flash`
- `gemini-2.5-flash`
- Other Gemini 2.x variants

### Single Tool Limitation

This tool cannot be combined with other tools in the same agent instance.

**Workaround (Python ADK):** ADK Python has a built-in workaround which bypasses this limitation by using `bypass_multi_tools_limit=True`.

### Display Obligations

When using Google Search grounding, search suggestions received in responses must be displayed in production applications. The UI code arrives as `renderedContent` in the Gemini response.

## Python API

### Import

```python
from google.adk.tools import google_search
```

### Usage Example

```python
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

agent = LlmAgent(
    name="search_agent",
    model="gemini-2.0-flash",
    tools=[google_search],
    instruction="You are a helpful assistant that can search the web."
)
```

### GoogleSearchTool Class

**Module Path:** `google.adk.tools.google_search_tool.GoogleSearchTool`

#### Methods

##### `process_llm_request()`

Processes requests from the language model to execute search operations.

**Note:** This method is called internally by the ADK framework when the LLM decides to use the search tool. It is not typically called directly by user code.

## Multi-Language Support

### TypeScript

```typescript
import { GOOGLE_SEARCH } from '@google/adk';

const agent = new Agent({
  name: 'search_agent',
  model: 'gemini-2.0-flash',
  tools: [GOOGLE_SEARCH]
});
```

### Go

```go
import "google.golang.org/adk/tool"

agent := &Agent{
    Model: "gemini-2.0-flash",
    Tools: []tool.Tool{
        geminitool.GoogleSearch{},
    },
}
```

### Java

```java
import com.google.adk.tools.GoogleSearchTool;

Agent agent = Agent.builder()
    .setModel("gemini-2.0-flash")
    .addTool(new GoogleSearchTool())
    .build();
```

## Configuration

Agents using this tool require:
1. Specification of a Gemini 2.x model
2. Appropriate session and runner setup for execution
3. Access to Google Search API (typically through Gemini API)

## Grounding Metadata

Search results are embedded in model responses. Access grounding metadata via `event.grounding_metadata` to retrieve:
- Source citations
- Search queries executed
- Retrieved content snippets

## Limitations

- **Single tool constraint:** Cannot be used alongside other tools in the same agent (Python has workaround)
- **Model restriction:** Only works with Gemini 2 models
- **Display requirement:** Must show search suggestions in production UIs

## Tool Type

**Type:** Built-in Gemini tool
**Execution:** Internally within the Gemini model (no local code execution required)

## Related Documentation

- [Google Search Grounding](https://google.github.io/adk-docs/grounding/google_search_grounding/)
- [Tool Limitations](https://google.github.io/adk-docs/tools/limitations/)
- [Gemini Models](https://google.github.io/adk-docs/agents/models/google-gemini/)

## References

- [Google Search - Agent Development Kit](https://google.github.io/adk-docs/integrations/google-search/)
- [Tools and Integrations for Agents](https://google.github.io/adk-docs/tools/)
- [Python API Reference](https://google.github.io/adk-docs/api-reference/python/)
