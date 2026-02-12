# Resume Stopped Agents - ADK Documentation

Source: https://google.github.io/adk-docs/runtime/resume/

## Overview

The Resume feature allows ADK agents to recover from interruptions like network failures or power loss without restarting entire workflows. Supported in ADK Python v1.14.0+, this capability enables workflows to "pick up where it left off."

## Enabling Resumability

Apply a `ResumabilityConfig` to your App object:

```python
app = App(
    name='my_resumable_agent',
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(
        is_resumable=True,
    ),
)
```

**Note:** This feature interacts differently with Long Running Functions, Confirmations, and Authentication requiring user input.

## Resuming Workflows

### Via API Request

```bash
# Restart API server if needed
adk api_server my_resumable_agent/

# Resume using curl
curl -X POST http://localhost:8000/run_sse \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "my_resumable_agent",
    "user_id": "u_123",
    "session_id": "s_abc",
    "invocation_id": "invocation-123"
  }'
```

### Via Runner Object

```python
runner.run_async(
    user_id='u_123',
    session_id='s_abc',
    invocation_id='invocation-123'
)
```

**Limitation:** The web interface and CLI don't currently support resume operations.

## How It Works

The system logs completed workflow tasks using Events and Event Actions. Upon resumption, it:

- Reinstates completed events for interrupted agents
- Resumes from the partially completed state
- Behavior varies by multi-agent type:
  - **Sequential Agent:** Reads `current_sub_agent` from saved state
  - **Loop Agent:** Uses `current_sub_agent` and `times_looped` values
  - **Parallel Agent:** Runs only incomplete sub-agents

**Caution:** Tools execute "at least once" when resuming, potentially multiple times. Idempotent tool design is essential for operations like purchases.

## Custom Agent Implementation

Custom agents require modifications to support resumability:

1. **Create CustomAgentState class** extending `BaseAgentState`
2. **Define WorkflowStep class** (optional) for sequential steps
3. **Set initial agent state** in async run function
4. **Add state checkpoints** after completed steps
5. **Set `end_of_agent=True`** upon full task completion

### Example Implementation

```python
class WorkflowStep(int, Enum):
    INITIAL_STORY_GENERATION = 1
    CRITIC_REVISER_LOOP = 2
    POST_PROCESSING = 3
    CONDITIONAL_REGENERATION = 4

class StoryFlowAgentState(BaseAgentState):
    step = WorkflowStep

async def _run_async_impl(self, ctx: InvocationContext):
    agent_state = self._load_agent_state(ctx, WorkflowStep)

    if agent_state is None:
        agent_state = StoryFlowAgentState(
            step=WorkflowStep.INITIAL_STORY_GENERATION
        )
        yield self._create_agent_state_event(ctx, agent_state)

    # Workflow steps with state checkpoints...
    yield self._create_agent_state_event(ctx, end_of_agent=True)
```

## Important Constraints

- Don't modify stopped workflows before resuming
- Custom agents aren't resumable by default
- Resume from the ADK Web UI isn't supported
