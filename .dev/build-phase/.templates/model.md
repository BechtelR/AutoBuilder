# Phase {N} Architecture Model
*Generated: {date}*

> This document assembles the architectural context for Phase {N}. The L1/L2
> architecture docs remain the source of truth — references throughout point
> to authoritative sections. Builders should read referenced sections for
> full design contracts.

## Overview
<!-- 2-3 sentences: what this phase builds, key architectural concerns -->

## Components

<!-- Every BOM component for this phase. Grouped by architecture layer. -->

```yaml
components:
  # --- {Layer Name} ---
  - id: {BOM_ID}
    name: {ComponentName}
    layer: {architecture_layer}
    type: deterministic | probabilistic
    responsibility: {what it does — one sentence}
    architecture_ref: {file} §{section}
    location: {file_path}
    satisfies: [CAP-{n}, ...]
```

## Component Diagram

<!-- Single Mermaid flowchart derived from the components and interfaces above. -->
<!-- Group into subgraphs by architecture layer. Show relationships with arrows. -->
<!-- This is a human verification aid — the YAML above is the authoritative source. -->

```mermaid
flowchart TD
    subgraph {LayerName}
        {ComponentName}
    end
```

## L2 Architecture Conformance

<!-- Derived from component architecture_refs above. Quick-reference for review. -->

| Component | Architecture Source |
|---|---|
| {ComponentName} | `{file}` §{section} |

## Interfaces

<!-- Typed contracts at non-trivial component boundaries. -->
<!-- Skip simple pass-through or single-method wrappers. -->

```yaml
interfaces:
  - from: {ComponentName}
    to: {ComponentName}
    sends: {TypeName}
    returns: {TypeName}
    notes: {behavioral expectations — omit if obvious}
```

## Key Types

<!-- Types that cross component boundaries. Not internal types. -->

```yaml
types:
  - name: {TypeName}
    kind: model | enum | typed_dict
    fields:
      - {field}: {type}   # {description, only if non-obvious}
    used_by: [{ComponentName}, ...]
```

## Data Flows

<!-- How data transforms across boundaries. One block per distinct non-trivial path. -->
<!-- Skip flows obvious from the interfaces. -->

```yaml
flows:
  - name: {flow_name}
    description: {one sentence}
    path:
      - step: {ComponentName}
        receives: {TypeName}
        emits: {TypeName}
        note: {transformation, only if non-obvious}
```

## Design Decisions

<!-- Decisions where the L2 architecture left options open for this phase. -->
<!-- These inform the builder — architecture docs remain authoritative. -->

| ID | Decision | Alternatives Considered | Rationale |
|----|----------|------------------------|-----------|

## Integration Points

<!-- Existing: what this phase connects to from prior phases. Future: extension points for later phases. -->

```yaml
integrations:
  existing:
    - component: {ComponentName}
      connects_to: {ExistingComponent}
      interface: {what's exchanged}

  future:
    - extension_point: {hook/registry/pattern}
      target_phase: Phase {X}
      preparation: {what this phase establishes}
```

## Notes

<!-- Constraints, gotchas, rabbit holes from FRD. Brief. -->
