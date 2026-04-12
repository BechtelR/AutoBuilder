---
name: prompt-improvement
description: >
  This skill should be used when the user asks to "improve this prompt",
  "optimize my prompt", "review this prompt", "make this prompt better",
  "fix my prompt", "prompt engineering help", "why isn't my prompt working",
  "rewrite this prompt", "improve prompt quality", or provides a prompt
  and asks for feedback, analysis, or enhancement. Also triggered by
  "improve-prompt" command invocation.
version: 0.1.0
---

# Prompt Improvement

Systematically analyze, diagnose, and improve prompts for LLM interactions. Applies evidence-based techniques from Anthropic, OpenAI, Google, and academic research to transform underperforming prompts into high-quality, production-ready instructions.

## Core Process

### Step 1: Classify the Prompt

Determine the prompt type — each has different optimization priorities:

| Type | Primary Focus | Key Techniques |
|------|--------------|----------------|
| **System prompt** | Identity, constraints, persistent behavior | Role definition, behavioral rules, output defaults |
| **User/task prompt** | Clarity, specificity, output format | Examples, decomposition, explicit constraints |
| **Agent instruction** | Context engineering, tool guidance, autonomy calibration | Action bias, tool descriptions, memory/state |
| **Tool description** | Precision, boundary definition, parameter docs | 3-4 sentence descriptions, examples, edge cases |
| **Skill/command** | Trigger accuracy, progressive disclosure, workflow | Imperative form, structured sections, reference delegation |

### Step 2: Diagnose Against 7 Dimensions

Score each dimension as STRONG (3) / ADEQUATE (2) / WEAK (1) / ABSENT (0). Sum for a total score out of 21, then route by severity:

| Total Score | Action | Rationale |
|-------------|--------|-----------|
| **0-7** | Full rewrite | Fundamental gaps across most dimensions |
| **8-13** | Targeted improvement | Fix the 2-3 weakest dimensions; preserve what works |
| **14-17** | Micro-improvements only | Prompt is already good; apply 1-2 surgical fixes if any |
| **18-21** | Affirm quality | State what makes it strong; suggest nothing unless genuinely valuable |

Focus improvement effort on the weakest dimensions first.

**The 7 Dimensions of Prompt Quality:**

1. **Clarity** — Are instructions specific, explicit, and unambiguous? Does the prompt specify format, length, style, and constraints? Does it explain *why* behind rules (enabling generalization)?

2. **Structure** — Are instructions, context, examples, and input clearly separated? Uses appropriate delimiters (XML tags for Claude, markdown headers for GPT)? Logical section ordering?

3. **Context** — Is sufficient grounding material provided? Environmental info (date, user profile, available tools)? Reference text where factual accuracy matters? Signal density over volume?

4. **Examples** — Are there 3-5 diverse few-shot demonstrations? Do examples cover edge cases, not just happy paths? Do they show the exact output format expected? Include reasoning traces for complex tasks?

5. **Reasoning** — For complex tasks, does the prompt encourage step-by-step thinking? Guided reasoning steps for multi-step problems? Structured thinking/answer separation? (Skip for simple retrieval/classification.)

6. **Output Control** — Is desired output format explicitly defined? Constraints on length, style, tone? Negative constraints for known failure modes? Permission to express uncertainty?

7. **Decomposition** — Is the task appropriately scoped for a single prompt? Should it be split into sequential subtasks? Is each subtask single-responsibility?

### Step 3: Detect Anti-Patterns

Scan for common failure modes. See `references/anti-patterns.md` for the full diagnostic catalog. The highest-impact anti-patterns:

- **Vague delegation** — "Write something good" with no format/constraints
- **Missing examples** — Instructions without demonstrations
- **Mega-prompt overload** — Too many responsibilities in one prompt
- **Implicit assumptions** — Relying on model to infer unstated requirements
- **Negative-only framing** — Listing what NOT to do without saying what TO do
- **Context flooding** — Including everything "just in case" instead of curating signal

### Step 4: Apply Targeted Improvements

Apply techniques matched to the diagnosed weaknesses. See `references/techniques.md` for the full technique catalog. Priority order:

1. **Fix clarity first** — Explicit instructions, specific constraints, motivation for rules
2. **Add structure** — XML tags, section separation, delimiter consistency
3. **Add examples** — 3-5 diverse demonstrations matching desired output format
4. **Specify output** — Format, length, style, tone, audience explicitly stated
5. **Add grounding** — Reference text, citation requirements, uncertainty permission
6. **Add reasoning** — Chain-of-thought sections for complex analytical tasks
7. **Decompose if needed** — Split overloaded prompts into focused subtasks

### Step 5: Validate the Improvement

Before presenting the improved prompt:

- [ ] Every instruction is actionable (verb-first, concrete)
- [ ] No ambiguous terms left undefined
- [ ] Output format explicitly specified
- [ ] Known failure modes addressed with constraints
- [ ] Examples present if task is format-sensitive
- [ ] Appropriate scope — neither overloaded nor trivially narrow
- [ ] Model-appropriate formatting (XML for Claude, markdown for GPT)
- [ ] Static content first, dynamic content last (cache-friendly)

## Output Format

Present improvements as a structured analysis:

```markdown
## Prompt Analysis

**Type:** [system prompt | user prompt | agent instruction | tool description | skill/command]
**Target Model:** [Claude | GPT | Gemini | model-agnostic]

### Dimension Scores
| Dimension | Score | Key Issue |
|-----------|-------|-----------|
| Clarity | WEAK | Vague instructions, no format specified |
| Structure | ABSENT | No delimiters or section separation |
| ... | ... | ... |

### Anti-Patterns Detected
1. [Anti-pattern name] — [Brief description of the instance]

### Improvements Applied
1. [What changed and why]

### Improved Prompt
[The rewritten prompt]

### Changelog
[Diff summary: what was added, removed, or restructured]
```

## Guidelines

- **Preserve intent** — Improve the prompt without changing what it's trying to accomplish
- **Minimal effective change** — Apply only the improvements that matter for this prompt type and task
- **Explain the why** — Each improvement should cite which dimension or anti-pattern it addresses
- **Respect the target model** — Claude prefers XML tags; GPT prefers markdown; adjust accordingly
- **Don't over-engineer** — A simple prompt for a simple task should stay simple. Not every prompt needs 5 examples and chain-of-thought. If the score is 14+, resist the urge to rewrite — surgical fixes only
- **Escalate decomposition** — If a prompt is trying to do too much, recommend splitting over heroic rewriting
- **Proportional response** — Match the intensity of improvement to the severity of the diagnosis. A 3/21 prompt needs a rewrite; a 16/21 prompt needs a one-line addition at most

## Additional Resources

### Reference Files

For detailed technique descriptions and diagnostic criteria, consult:

- **`references/techniques.md`** — Complete catalog of prompt engineering techniques with when/how to apply each, sourced from Anthropic, OpenAI, Google, and academic research
- **`references/anti-patterns.md`** — Diagnostic anti-patterns with detection criteria, severity ratings, and targeted fixes
- **`references/examples.md`** — Before/after prompt transformations across prompt types demonstrating techniques in practice
