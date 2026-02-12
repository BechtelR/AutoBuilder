# Context Compression - Agent Development Kit

## Overview

The Context Compression feature reduces agent processing times by summarizing older workflow event history as context grows. It implements a sliding window approach within Sessions to manage the accumulation of user instructions, retrieved data, tool responses, and generated content.

## Configure Context Compaction

Add compression to your agent by including an `EventsCompactionConfig` in your App object:

```python
from google.adk.apps.app import App
from google.adk.apps.app import EventsCompactionConfig

app = App(
    name='my-agent',
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Trigger compaction every 3 new invocations
        overlap_size=1          # Include last invocation from previous window
    ),
)
```

The ADK Runner handles background compression automatically when sessions reach configured intervals.

## Example of Context Compaction

With `compaction_interval=3` and `overlap_size=1`, compression occurs at events 3, 6, 9, etc.:

1. **Event 3 completes**: All 3 events compressed into summary
2. **Event 6 completes**: Events 3-6 compressed with 1-event overlap
3. **Event 9 completes**: Events 6-9 compressed with 1-event overlap

## Configuration Settings

- **`compaction_interval`**: Number of completed events triggering compression
- **`overlap_size`**: Previously compacted events included in new compression
- **`summarizer`**: (Optional) Custom AI model for summarization

## Define a Custom Summarizer

Specify a particular model using `LlmEventSummarizer`:

```python
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models import Gemini

summarization_llm = Gemini(model="gemini-2.5-flash")
my_summarizer = LlmEventSummarizer(llm=summarization_llm)

app = App(
    name='my-agent',
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1,
        summarizer=my_summarizer,
    ),
)
```

**Feature availability**: Supported in ADK Python v1.16.0

---

**Source**: https://google.github.io/adk-docs/context/compaction/
**Downloaded**: 2026-02-11
