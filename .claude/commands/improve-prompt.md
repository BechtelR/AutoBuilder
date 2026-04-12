---
description: Analyze and improve prompts using evidence-based prompt engineering techniques
argument-hint: "<prompt-text-or-file-path> [--type=system|user|agent|tool|skill] [--model=claude|gpt|gemini] [--brief]"
---

<objective>
Analyze and improve the provided prompt using evidence-based prompt engineering techniques.

Read the prompt-improvement skill at `.claude/skills/prompt-improvement/SKILL.md` for the full analysis framework, dimensions, and guidelines. Reference files in `.claude/skills/prompt-improvement/references/` provide technique catalogs, anti-pattern diagnostics, and before/after examples.
</objective>

<context>
{ARGUMENTS}

If a file path is provided, read the file contents as the prompt to analyze. If quoted text is provided, use it directly.

**Parse arguments:**
- `--type`: Prompt type override (system, user, agent, tool, skill). If omitted, auto-detect from content.
- `--model`: Target model (claude, gpt, gemini). Default: claude.
- `--brief`: Output only the improved prompt with a short changelog, skip the full analysis table.
</context>

<process>
Run the 5-step analysis process from the skill:

1. **Classify** the prompt type (Step 1 in SKILL.md)
2. **Diagnose** against the 7 dimensions: Clarity, Structure, Context, Examples, Reasoning, Output Control, Decomposition (Step 2)
3. **Detect anti-patterns** — consult `references/anti-patterns.md` for the diagnostic catalog (Step 3)
4. **Apply targeted improvements** — consult `references/techniques.md` for technique selection matched to diagnosed weaknesses (Step 4)
5. **Validate** the improved prompt against the checklist (Step 5)

Present results in the structured output format defined by the skill:
- Dimension score table
- Anti-patterns detected
- Improvements applied (with rationale)
- The improved prompt
- Changelog (diff summary)

If `--brief` was specified, skip the dimension table and anti-pattern list — output only the improved prompt and a concise changelog.

6. **Write the improved prompt** to `.claude/.prompts/improved/`. Derive the filename from the prompt's purpose or source:
   - If source was a file: use the source filename (e.g., `my-prompt.md` → `.claude/.prompts/improved/my-prompt.md`)
   - If source was inline text: derive a short kebab-case name from the prompt's purpose (e.g., `api-review-system-prompt.md`)
   - Always write without asking — this is the canonical output location for improved prompts
   - If the prompt source was also a file, ask before overwriting the *original* (the improved copy in `.prompts/improved/` is always written)
</process>

<success_criteria>
- Prompt classified and diagnosed against all 7 dimensions
- Anti-patterns identified (or explicitly noted as absent)
- Improvements applied with rationale citing specific dimensions or anti-patterns
- Improved prompt presented in full
- Changelog summarizing what changed and why
- Improved prompt written to `.claude/.prompts/improved/{filename}.md`
</success_criteria>
