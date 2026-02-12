# google.adk.evaluation - Agent Evaluation Module

**Module**: `google.adk.evaluation`
**Purpose**: Agent evaluation framework for assessing probabilistic agent performance
**Documentation Source**: https://google.github.io/adk-docs/evaluate/

---

## Overview

The Agent Development Kit (ADK) provides evaluation capabilities for assessing agent performance beyond traditional pass/fail testing. Due to LLM probabilistic nature, the framework emphasizes qualitative evaluation of both final outputs and agent decision sequences.

---

## Core Evaluation Components

### Two Evaluation Approaches

#### 1. Test Files (.test.json)

Single agent-model interactions designed for unit testing during active development. Each file contains one session with multiple turns.

- **Schema**: Backed by Pydantic schemas: `EvalSet` and `EvalCase`
- **Purpose**: Unit testing during active development
- **Structure**: One session with multiple turns per file

#### 2. Evalset Files (.evalset.json)

Multiple sessions suited for integration testing complex, multi-turn conversations.

- **Requirement**: Vertex Gen AI Evaluation Service API (paid service)
- **Capability**: Dynamic user simulation via conversation scenarios
- **Purpose**: Integration testing for complex interactions

---

## What Gets Evaluated

### 1. Trajectory Analysis

Agents typically perform action sequences before responding. The framework compares actual tool use trajectories against expected ones.

**Example**:
```python
expected_steps = [
    "determine_intent",
    "use_tool",
    "review_results",
    "report_generation"
]
```

### 2. Response Quality

Final output assessed for:
- Relevance
- Correctness
- Quality

---

## Evaluation Criteria

ADK provides eight built-in evaluation criteria:

### Reference-Based Metrics

#### tool_trajectory_avg_score
- **Type**: Reference-based
- **Purpose**: Exact tool call sequence matching
- **Modes**: EXACT, IN_ORDER, or ANY_ORDER matching
- **Default Threshold**: 1.0 (100% match)

#### response_match_score
- **Type**: Reference-based
- **Purpose**: ROUGE-1 similarity scoring
- **Method**: Word overlap with reference responses
- **Default Threshold**: 0.8

#### final_response_match_v2
- **Type**: LLM-judged
- **Purpose**: Semantic equivalence to reference answers
- **Method**: LLM-based assessment

### Quality Assessment Metrics

#### rubric_based_final_response_quality_v1
- **Type**: Quality assessment
- **Purpose**: Evaluates response quality against custom rubrics
- **Configuration**: Accepts custom rubric definitions with unique IDs

#### rubric_based_tool_use_quality_v1
- **Type**: Quality assessment
- **Purpose**: Assesses tool usage quality based on defined criteria
- **Configuration**: Rubric-based evaluation of tool calls

### Safety & Grounding Metrics

#### hallucinations_v1
- **Type**: Safety check
- **Purpose**: Detects unsupported claims
- **Method**: Validates sentences against context

#### safety_v1
- **Type**: Safety check
- **Purpose**: Harmlessness evaluation
- **Implementation**: Delegates to Vertex AI General AI Eval SDK

#### per_turn_user_simulator_quality_v1
- **Type**: Simulation quality
- **Purpose**: Validates user simulator adherence to conversation plans
- **Use Case**: Dynamic user simulation scenarios

---

## Execution Methods

### 1. Web UI (`adk web`)

Interactive interface providing:
- Test case creation
- Session viewing
- Metric configuration
- Results analysis with pass/fail comparisons

**Usage**:
```bash
adk web
```

### 2. Programmatic Testing (`pytest`)

Integrate evaluations into CI/CD pipelines using `AgentEvaluator.evaluate()` method.

**Example**:
```python
from google.adk.evaluation import AgentEvaluator

evaluator = AgentEvaluator(agent=my_agent)
results = await evaluator.evaluate(test_file_path="tests/my_test.test.json")
```

### 3. Command Line (`adk eval`)

**Usage**:
```bash
adk eval <AGENT_MODULE_FILE_PATH> <EVAL_SET_FILE_PATH> [--config_file_path=<PATH>]
```

**Filtering specific evals**:
```bash
adk eval agent.py tests/file.json:eval_1,eval_2
```

---

## Configuration

### Test Configuration Structure

Custom criteria defined in `test_config.json`:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 1.0,
    "response_match_score": 0.8
  }
}
```

### Configuration Properties

- **Simple criteria**: Accept float thresholds (0.0-1.0)
- **Complex criteria**: Use objects with nested configurations
- **LLM-based evaluation**: Support configurable judge models
- **Sampling**: `num_samples` parameter for multiple evaluations
- **Voting**: Majority voting across multiple evaluations for robustness

### Rubrics Definition

Custom rubrics require:
- **Unique IDs**: Each rubric must have a unique identifier
- **Text properties**: Describing evaluation aspects
- **Flexible quality assessment**: Beyond fixed metrics

---

## Test Case Structure

Evaluation cases include:

| Field | Description |
|-------|-------------|
| `user_content` | User query/input |
| `expected_intermediate_tool_use` | Tool calls in expected order |
| `expected_intermediate_responses` | Sub-agent outputs |
| `final_response` | Expected agent conclusion |

---

## User Simulation

For conversational agents where user responses vary, evaluations can dynamically generate prompts via AI models rather than using fixed prompts.

**Use Case**: Multi-turn conversations with unpredictable user behavior

---

## Score Interpretation

All criteria return normalized scores between **0.0-1.0**, where:
- **1.0**: Perfect performance
- **0.0**: Complete failure
- Higher values indicate better performance across respective dimensions

---

## Migration Support

ADK provides migration utilities for legacy test files:

```python
from google.adk.evaluation import AgentEvaluator

AgentEvaluator.migrate_eval_data_to_new_schema(
    old_file_path="tests/legacy_test.json",
    new_file_path="tests/migrated_test.test.json"
)
```

**Purpose**: Convert legacy test files to Pydantic-backed schema format

---

## Key Classes and Types

### EvalSet
Pydantic model representing a collection of evaluation cases.

### EvalCase
Pydantic model representing a single evaluation test case.

### EvalConfig
Configuration object for evaluation criteria and thresholds.

### AgentEvaluator
Main class for running evaluations programmatically.

**Methods**:
- `evaluate()`: Run evaluation on test files
- `migrate_eval_data_to_new_schema()`: Convert legacy tests

---

## Best Practices

1. **Use appropriate thresholds**: Default 1.0 for trajectories, 0.8 for responses
2. **Test during development**: Use .test.json files for unit testing
3. **Integration testing**: Use .evalset.json for complex scenarios
4. **Custom rubrics**: Define domain-specific quality criteria
5. **CI/CD integration**: Run evaluations in automated pipelines
6. **User simulation**: Enable dynamic testing for conversational agents

---

## Related Documentation

- [Evaluation Criteria Details](https://google.github.io/adk-docs/evaluate/criteria/)
- [User Simulation Guide](https://google.github.io/adk-docs/evaluate/user-sim/)
- [ADK Web UI](https://google.github.io/adk-docs/get-started/quickstart/)

---

**Last Updated**: 2026-02-11
**API Stability**: Stable
