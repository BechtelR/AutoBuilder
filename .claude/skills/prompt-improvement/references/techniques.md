# Prompt Engineering Techniques — Complete Catalog

Comprehensive reference of evidence-based prompt improvement techniques. Each technique includes when to apply, how to apply, and source attribution.

---

## 1. Clarity and Specificity

**When:** Always. The single highest-impact improvement for any prompt.

**How to apply:**
- Specify desired output format, length, style, tone, and audience explicitly
- Use numbered steps when order or completeness matters
- Provide motivation for constraints — explain *why*, not just *what* ("Never use ellipses because TTS cannot pronounce them" enables the model to generalize to similar edge cases)
- Tell the model what TO do, not just what NOT to do
- Define ambiguous terms the first time they appear

**Example transformation:**
```
BEFORE: "Summarize this document"
AFTER:  "Summarize this document in 3-5 bullet points, each under 20 words.
         Focus on actionable findings. Use present tense. Audience: engineering leads."
```

**Sources:** Anthropic Prompt Engineering Guide, OpenAI Best Practices, Google Whitepaper

---

## 2. Structured Formatting (XML Tags / Delimiters)

**When:** Any prompt with multiple content types (instructions + context + examples + input). Critical for prompts over ~200 words.

**How to apply:**
- Wrap each content section in descriptive tags: `<instructions>`, `<context>`, `<examples>`, `<input>`, `<output_format>`
- Use consistent tag names throughout the prompt
- Nest for hierarchy: `<document><source>...</source><content>...</content></document>`
- Reference tags in instructions: "Using the context in `<context>` tags, answer the question in `<question>` tags"
- **Claude**: Prefers XML tags (trained on XML-structured data)
- **GPT**: Prefers markdown headers and formatting
- **Universal**: Any consistent delimiter scheme works; consistency matters more than specific format

**Sources:** Anthropic XML Tags Guide, OpenAI Prompt Engineering Guide

---

## 3. Few-Shot Examples (Multishot Prompting)

**When:** Format-sensitive tasks, classification, structured output, any task where instructions alone produce inconsistent results. Try zero-shot first; add examples only if quality is insufficient.

**How to apply:**
- Include 3-5 diverse, relevant examples
- Wrap in `<examples><example>...</example></examples>` tags
- Show both positive and negative examples where useful
- Examples should cover edge cases and desired variation, not just the happy path
- Match the exact output format expected
- Include reasoning traces in examples for complex tasks
- Place examples after instructions, before actual input

**Key insight:** "Three good examples beat a page of instructions." Examples are the single most reliable way to steer output format, tone, and reasoning approach.

**Sources:** Google Whitepaper, Anthropic Multishot Guide, OpenAI Guide, The Prompt Report (2024)

---

## 4. Chain-of-Thought (CoT)

**When:** Complex multi-step problems, math, analysis, reasoning tasks. Do NOT apply to simple retrieval, classification, or straightforward generation — CoT adds latency without benefit.

**Three levels of sophistication:**

1. **Basic:** Append "Think step by step" to the prompt
2. **Guided:** Outline specific reasoning steps: "First, identify the key variables. Then, analyze their relationships. Finally, draw a conclusion."
3. **Structured:** Separate reasoning from output with tags: `<thinking>` for reasoning, `<answer>` for the final response

**Critical rule (prompt-level CoT):** When using `<thinking>`/`<answer>` tags in the prompt (not API-level thinking), the model must output its reasoning as text. Reasoning only occurs when text is produced.

**For Claude 4.6 (API-level thinking):** Use `thinking: {type: "adaptive"}` with appropriate effort level. Adaptive thinking outperforms fixed-budget extended thinking. Prefer general instructions ("think thoroughly") over prescriptive step-by-step plans -- the model's reasoning frequently exceeds what a human would prescribe.

**Sources:** Chain-of-Thought research (Wei et al.), Anthropic CoT Guide, Google Whitepaper

---

## 5. System Prompt / Role Assignment

**When:** Agent/assistant applications, persistent behavioral requirements, establishing expertise baseline.

**How to apply:**
- Define specific identity and expertise: "You are a senior security engineer specializing in Python applications"
- Set action bias explicitly:
  - Proactive: "Implement changes rather than only suggesting them"
  - Cautious: "Provide recommendations only; do not make changes without explicit approval"
- Place persistent behavioral rules in system prompt (applied across conversation)
- Provide environmental context: current date, user profile, available tools, constraints
- Role is supplementary — clear instructions matter more than persona
- Claude 4.6+ calibration: these models are more proactive by default. Anti-laziness prompts ("CRITICAL: You MUST use this tool") that were needed for older models may cause overtriggering. Use measured language instead

**Sources:** Anthropic System Prompts Guide, Anthropic Prompting Best Practices (2026), Google Whitepaper, OpenAI Guide

---

## 6. Grounding and Hallucination Reduction

**When:** Factual tasks, document QA, any task where accuracy matters more than creativity.

**How to apply:**
- Include reference documents wrapped in `<document>` tags with `<source>` metadata
- Restrict to provided context: "Only use information from the provided documents"
- Require citations: "Cite the source document for each claim"
- Direct quote extraction: "First extract relevant quotes, then answer based on those quotes"
- Grant permission to say "I don't know" — explicitly allowing uncertainty drastically reduces fabrication
- Verification step: "Verify each claim by finding a supporting quote. Retract claims without support."

**Sources:** Anthropic Hallucination Guide, OpenAI Guide, Google Prompting Strategies

---

## 7. Output Format Control

**When:** Any task where output format matters (most production use cases).

**How to apply:**
- Specify format precisely: JSON, XML, YAML, markdown, CSV, plain text
- Provide a schema or template for structured outputs
- Use tool definitions with enum fields for classification
- For JSON: provide the exact schema with field descriptions
- Specify constraints: max length, required fields, forbidden content
- For Claude 3.x/4.5: prefill the assistant response with the format opening (e.g., `{`)
- Claude 4.6+: assistant prefill on last turn is no longer supported. Use structured outputs, tool definitions with schemas, or explicit format instructions instead

**Sources:** Anthropic Output Control, OpenAI Guide

---

## 8. Task Decomposition / Prompt Chaining

**When:** The prompt is trying to do too many things. A reliable signal: if the task cannot be described in one sentence, decompose it.

**How to apply:**
- Identify distinct, sequential steps in the task
- Create separate prompts for each step, each with a single clear objective
- Pass structured output from one step as input to the next (XML tags work well for handoffs)
- Self-correction pattern: Generate draft -> Review against criteria -> Refine based on review (each a separate call)
- Each subtask prompt can use richer, more targeted examples than a monolithic prompt

**Academic validation:** Decomposed prompting significantly outperforms both few-shot and chain-of-thought on complex tasks (ICLR 2023).

**Sources:** Anthropic Prompt Chaining Guide, OpenAI Guide, Decomposed Prompting (ICLR 2023)

---

## 9. Long Context Management

**When:** Prompts with >20K tokens of context, multi-document inputs.

**How to apply:**
- Place long documents at the top, above queries and instructions
- Place the actual question/task at the end — improves response quality by up to 30%
- Wrap multiple documents with metadata: `<document><source>filename</source><content>...</content></document>`
- Ask model to extract relevant quotes first, then perform the task
- Curate for signal density — context has diminishing returns ("context rot")

**Sources:** Anthropic Long Context Tips, Google Whitepaper

---

## 10. Negative Constraints and Guardrails

**When:** Known failure modes exist, the model tends toward specific unwanted behaviors.

**How to apply:**
- Pair negative constraints with positive alternatives: "Do not summarize the data. Instead, provide the raw numbers in a table."
- Address specific observed failure modes, not hypothetical ones
- Use "Do not..." for hard boundaries, "Prefer X over Y" for soft guidance
- For safety: place constitutional constraints at the top, mark as non-overridable

**Sources:** Anthropic Best Practices, OpenAI Guide

---

## 11. Self-Refinement

**When:** Tasks where a second pass demonstrably improves quality (writing, analysis, complex generation). Not needed for simple/deterministic tasks.

**How to apply:**
- Generate -> Critique -> Improve cycle within the prompt or as chained calls
- Provide specific critique criteria: "Review your response for factual accuracy, completeness, and tone"
- The critique step should reference the original requirements explicitly
- Lightweight variant: append "Before finishing, verify your answer against [criteria]" for self-checking without a full refinement cycle. Effective for math and coding tasks
- ~20% average improvement across diverse tasks (Self-Refine, Madaan et al. 2023)

**Sources:** Self-Refine (Madaan et al., 2023), DSPy, OPRO

---

## 12. Tool Description Engineering

**When:** Any prompt that involves tool/function calling.

**How to apply:**
- Write 3-4+ sentences per tool description, including purpose, example usage, edge cases, and boundaries from other tools
- Use namespacing for related tools: `files_search`, `files_read`, `files_write`
- Show concrete input/output examples alongside schemas
- Tool descriptions steer agent behavior as much as system prompts
- Return only high-signal information from tool implementations

**Key insight:** Small refinements to tool descriptions yield dramatic improvements in agent performance (demonstrated on SWE-bench).

**Sources:** Anthropic Tool Design Guide, OpenAI Guide

---

## 13. Cache-Friendly Ordering

**When:** Production prompts where cost and latency matter.

**How to apply:**
- Place static content first: system instructions, few-shot examples, tool definitions
- Place variable content last: user input, session data, dynamic context
- Keep prompt component ordering identical between requests
- Even small changes in early tokens invalidate prefix-match caching
- All major providers (Anthropic, OpenAI, AWS) use exact prefix matching

**Sources:** Anthropic Prompt Caching Docs, OpenAI Prompt Caching Guide

---

## 14. Context Engineering (Agentic Systems)

**When:** Multi-turn agents, long-running systems, agents with memory/tools/state.

**How to apply:**
- Context = system prompt + user message + tools + memory + retrieved docs + conversation history + state — all is engineering surface area
- Structured note-taking: agent writes persistent notes outside context window, pulled back when needed
- Context compaction: summarize conversation when approaching window limits
- Different initialization prompts for first context window vs. subsequent windows
- Treat context as a managed resource: what goes in, what stays, what gets summarized, what gets evicted
- Signal density over volume — diminishing returns from context flooding
- Claude 4.6+: models have context awareness (track remaining token budget). Inform the agent about compaction behavior so it does not prematurely wrap up work
- Use filesystem and git for state persistence across context windows rather than relying solely on in-context memory
- Subagent orchestration: delegate independent workstreams to subagents; avoid spawning subagents for simple sequential tasks

**Sources:** Anthropic Context Engineering (2025), ACE Framework, Anthropic Long-Running Agents Guide, Anthropic Prompting Best Practices (2026)
