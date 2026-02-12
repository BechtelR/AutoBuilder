# ADK Evaluation Criteria Documentation

Source: https://google.github.io/adk-docs/evaluate/

## Overview

The Agent Development Kit provides eight evaluation criteria for assessing agent performance across tool use, response quality, and safety dimensions.

## Criteria Summary Table

| Criterion | Purpose | Reference-Based | Requires Rubrics | LLM-as-Judge |
|-----------|---------|-----------------|------------------|--------------|
| `tool_trajectory_avg_score` | Tool call sequence matching | Yes | No | No |
| `response_match_score` | ROUGE-1 similarity | Yes | No | No |
| `final_response_match_v2` | Semantic equivalence judgment | Yes | No | Yes |
| `rubric_based_final_response_quality_v1` | Custom quality rubrics | No | Yes | Yes |
| `rubric_based_tool_use_quality_v1` | Tool usage quality rubrics | No | Yes | Yes |
| `hallucinations_v1` | Context grounding verification | No | No | Yes |
| `safety_v1` | Harmlessness assessment | No | No | Yes |
| `per_turn_user_simulator_quality_v1` | Conversation plan adherence | No | No | Yes |

## Key Criteria Details

### tool_trajectory_avg_score

Compares agent tool calls against expected sequences using three match strategies:

- **EXACT**: Perfect correspondence required with no deviations
- **IN_ORDER**: Expected tools must appear sequentially but other calls allowed between them
- **ANY_ORDER**: Expected tools must appear but sequence irrelevant

Scores range 0.0-1.0, with 1.0 indicating complete alignment across all invocations.

### response_match_score

Measures word-level overlap between agent output and reference using ROUGE-1 metrics. Produces scores between 0.0 and 1.0, where higher indicates greater lexical similarity.

### final_response_match_v2

"Uses a Large Language Model as a judge to determine if the agent's final response is semantically equivalent to the provided reference response." Employs majority voting across multiple samples for robustness. Returns 0.0-1.0 scores based on validity judgments.

### rubric_based_final_response_quality_v1

Enables custom quality assessment through user-defined rubrics evaluating attributes like conciseness, tone, and helpfulness. LLM judges each rubric independently, producing per-rubric and overall scores.

### rubric_based_tool_use_quality_v1

Assesses tool selection, parameter accuracy, and call sequencing through custom rubrics. Useful for validating agent reasoning processes and prescribed workflows.

### hallucinations_v1

Two-step evaluation: segments responses into sentences, then validates each against context (instructions, tool outputs, definitions). Produces accuracy score representing percentage of supported/applicable statements.

### safety_v1

Delegates safety assessment to Vertex AI General AI Eval SDK, requiring Google Cloud Project configuration. Scores range 0.0-1.0, with higher values indicating safer content.

### per_turn_user_simulator_quality_v1

Evaluates whether user simulators follow defined conversation plans across multi-turn exchanges. First-turn responses validated against `starting_prompt`; subsequent turns judged against `conversation_plan`.

## Configuration Examples

Basic threshold configuration:
```json
{
  "criteria": {
    "response_match_score": 0.8
  }
}
```

Advanced LLM-judge configuration:
```json
{
  "criteria": {
    "final_response_match_v2": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash",
        "num_samples": 5
      }
    }
  }
}
```

Rubric-based evaluation example:
```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash",
        "num_samples": 5
      },
      "rubrics": [
        {
          "rubric_id": "conciseness",
          "rubric_content": {
            "text_property": "Response is direct and to the point"
          }
        }
      ]
    }
  }
}
```

## Implementation Notes

- LLM-based criteria support configurable judge models and sampling counts for robustness
- Reference-based criteria require golden/expected outputs for comparison
- Rubric-based criteria enable domain-specific quality assessment beyond standard metrics
- Safety evaluation requires Google Cloud Project with proper environment variable configuration
