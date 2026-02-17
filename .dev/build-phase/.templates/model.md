# Phase {N} Model: {Phase Title}
*Generated: {date}*

## Component Diagram

```mermaid
{Mermaid flowchart showing components, their relationships, and which architecture layer each belongs to (Interface / Gateway / Worker / Engine / Infrastructure). Group components into subgraphs by layer. Show data flow direction with arrows. For UI components: names + relationships only — detailed UI design lives in separate files for dashboard phases.}
```

## Deliverable-to-Component Traceability

| Deliverable | Components |
|---|---|
| P{N}.D{n} | {components this deliverable maps to} |

## Major Interfaces

{Protocol classes and ABCs with method signatures only — no implementation bodies. One code block per interface. Include docstrings for non-obvious methods. These define the contracts between components.}

```python
class {InterfaceName}(Protocol):
    """{Single-line purpose.}"""

    async def {method}(self, {params}: {types}) -> {return_type}:
        """Optional clarification."""
        ...
```

(repeat for all interfaces)

## Key Type Definitions

{Pydantic models, enums, and TypedDicts at system boundaries. Field-level detail — every field with its type and purpose. Group by domain concept.}

```python
class {ModelName}(BaseModel):
    """{Purpose.}"""
    {field}: {type}  # {purpose}
```

```python
class {EnumName}(str, enum.Enum):
    {MEMBER} = "{MEMBER}"  # {meaning}
```

(repeat for all types)

## Data Flow

{How data transforms across architecture layers. Show the type chain — what enters each boundary and what exits. Use a table or Mermaid sequence diagram.}

```mermaid
{Sequence or flowchart showing data transformation: external input → gateway Pydantic model → DB model → worker DTO → engine state → output artifact. Label each arrow with the transformation.}
```

## Logic / Process Flow

{State machines, pipeline stages, decision trees. Structured text or Mermaid state diagrams. No implementation code — describe transitions, conditions, and outcomes.}

```mermaid
stateDiagram-v2
    {State diagram showing lifecycle, transitions, and conditions}
```

## Integration Points

### Existing System
{Components this phase connects to that already exist. For each: what it is, how this phase uses it, the interface boundary.}

| Component | Interface | How This Phase Uses It |
|-----------|-----------|----------------------|
| {existing component} | {protocol/API/state key} | {description} |

### Future Phase Extensions
{Known extension points for later phases. What hooks, registries, or patterns this phase establishes that future work will consume.}

| Extension Point | Future Phase | Preparation |
|----------------|-------------|-------------|
| {hook/registry/pattern} | Phase {X} | {what this phase provides} |

## Notes

{Constraints, gotchas, non-obvious decisions, performance considerations. Keep brief — if it needs a paragraph, it belongs in the spec's Design Decisions.}
