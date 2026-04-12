# Prompt Anti-Patterns — Diagnostic Catalog

Common prompt failure modes with detection criteria, severity, and targeted fixes.

---

## 1. Vague Delegation

**Severity:** CRITICAL
**Detection:** Prompt lacks specific format, length, style, or constraint specifications. Contains phrases like "write something good", "help me with", "do your best".

**Fix:** Add explicit specifications for every dimension of the desired output:
- Format (JSON, bullets, prose, table)
- Length (word count, number of items)
- Style/tone (technical, casual, formal)
- Audience (engineer, executive, beginner)
- Constraints (what to include/exclude)

---

## 2. Missing Examples

**Severity:** HIGH
**Detection:** Prompt contains format-sensitive instructions but zero demonstrations. The model must infer output structure entirely from description.

**Fix:** Add 3-5 diverse examples showing exact input-to-output transformations. Wrap in `<examples>` tags. Prioritize edge cases over happy paths — the model already handles typical cases well.

---

## 3. Mega-Prompt Overload

**Severity:** HIGH
**Detection:** Single prompt attempts 3+ distinct responsibilities. Contains multiple unrelated instruction blocks. Length exceeds ~2000 words without clear section structure.

**Fix:** Decompose into focused subtask prompts. Each prompt gets one clear objective. Chain outputs between prompts using structured handoffs. If decomposition isn't possible, at minimum add clear section structure with delimiters.

---

## 4. Implicit Assumptions

**Severity:** HIGH
**Detection:** Prompt relies on the model to infer unstated requirements. Key terms are undefined. Success criteria are not explicit. Think of it as: "Would a smart person with zero context about my project understand exactly what I want?"

**Fix:** State every assumption explicitly. Define domain terms. Provide environmental context (date, user profile, available tools). Specify success criteria.

---

## 5. Negative-Only Framing

**Severity:** MEDIUM
**Detection:** Prompt is primarily a list of "don't do X" constraints without corresponding "do Y instead" guidance. The model knows what to avoid but not what to pursue.

**Fix:** Pair every negative constraint with a positive alternative: "Do not summarize. Instead, provide the raw data in a markdown table with columns for [X, Y, Z]."

---

## 6. Context Flooding

**Severity:** MEDIUM
**Detection:** Prompt includes large amounts of context "just in case" without curation for relevance. Long documents dumped without guidance on which parts matter.

**Fix:** Curate context for signal density. Include only material directly relevant to the task. For long documents, tell the model which sections to focus on, or ask it to extract relevant quotes before performing the task.

---

## 7. No Output Format Specification

**Severity:** MEDIUM
**Detection:** Prompt describes the task but not the desired output structure. No mention of format, schema, template, or structural requirements.

**Fix:** Explicitly define output format. For structured data, provide a JSON schema or template. For text, specify section structure, length, and style. Show an example of the desired output.

---

## 8. Missing Reasoning Scaffolding

**Severity:** MEDIUM (for complex tasks only)
**Detection:** Prompt asks for a complex analytical answer (comparison, evaluation, multi-step reasoning) but provides no space or instruction for the model to reason through the problem.

**Fix:** Add chain-of-thought instruction: guided steps for the reasoning process, or `<thinking>`/`<answer>` separation. For simpler tasks, this anti-pattern does not apply — skip it.

---

## 9. Flat Structure

**Severity:** MEDIUM
**Detection:** Prompt is a single block of text with no delimiters, headers, or section separation. Instructions, context, examples, and input are intermixed.

**Fix:** Add structure using XML tags (for Claude) or markdown headers (for GPT). Separate: instructions, context/reference material, examples, input, and output format specification.

---

## 10. Wrong Granularity Role

**Severity:** LOW-MEDIUM
**Detection:** Role assignment is either too generic ("You are a helpful assistant") to add value, or too narrow ("You are a Python 3.11 asyncio expert who only knows FastAPI") to handle the actual task scope.

**Fix:** Match role specificity to task scope. Include expertise level and perspective relevant to the actual work. "You are a senior backend engineer reviewing a pull request for security and performance issues" is better than either extreme.

---

## 11. Cache-Hostile Ordering

**Severity:** LOW (cost/latency impact only)
**Detection:** Variable content (user input, dynamic data) appears before static content (system instructions, examples, tool definitions) in the prompt.

**Fix:** Reorder: static content first (system prompt, examples, tool schemas), dynamic content last (user input, session-specific data). This maximizes prefix-match cache hits.

---

## 12. Model-Inappropriate Formatting

**Severity:** LOW
**Detection:** Prompt uses formatting conventions mismatched to the target model. E.g., markdown headers for Claude when XML tags would be more effective, or XML for GPT models.

**Fix:** Use the format the target model responds best to:
- **Claude:** XML tags for structure, markdown within content sections
- **GPT:** Markdown headers and formatting throughout
- **Model-agnostic:** Any consistent delimiter scheme; consistency matters more than specific format
