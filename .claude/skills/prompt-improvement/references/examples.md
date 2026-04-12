# Before/After Prompt Transformations

Concrete demonstrations of prompt improvement techniques applied across different prompt types.

---

## Example 1: Vague Task Prompt → Clear, Structured Prompt

**Prompt Type:** User/task prompt
**Primary Issues:** Vague delegation, no output format, no examples, flat structure
**Techniques Applied:** Clarity, structure, output control, examples

### Before

```
Analyze this code and tell me if there are any issues.
```

### After

```xml
<instructions>
Analyze the code in <code> for the following categories of issues:
1. Security vulnerabilities (injection, auth bypass, data exposure)
2. Performance problems (N+1 queries, unnecessary allocations, blocking I/O)
3. Logic errors (off-by-one, null handling, race conditions)

For each issue found, provide:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Line number(s) affected
- Description of the issue (1-2 sentences)
- Suggested fix (code snippet)

If no issues are found in a category, state "None found" for that category.
</instructions>

<output_format>
## Security
| Severity | Lines | Issue | Fix |
|----------|-------|-------|-----|

## Performance
| Severity | Lines | Issue | Fix |
|----------|-------|-------|-----|

## Logic
| Severity | Lines | Issue | Fix |
|----------|-------|-------|-----|
</output_format>

<code>
{user_code_here}
</code>
```

**Why this works:** Every dimension of the output is specified. The model knows exactly what to look for, how to structure findings, and what to do when nothing is found.

---

## Example 2: Overloaded System Prompt → Focused + Decomposed

**Prompt Type:** System prompt (agent)
**Primary Issues:** Mega-prompt overload, implicit assumptions, no action bias
**Techniques Applied:** Decomposition, role definition, action bias, output control

### Before

```
You are an AI assistant that helps with writing, coding, data analysis, 
research, creative tasks, and general knowledge questions. Be helpful, 
accurate, and thorough. Follow best practices. Ask clarifying questions 
when needed. Format your responses nicely.
```

### After (focused on a specific role)

```xml
<identity>
Senior Python code reviewer specializing in async web applications.
Expertise: FastAPI, SQLAlchemy 2.0, Redis, asyncio patterns.
</identity>

<action_bias>
Default to providing specific, actionable code fixes — not just descriptions 
of problems. When the fix is straightforward, show the corrected code. When 
the fix requires design decisions, present 2 options with trade-offs and a 
recommendation.
</action_bias>

<behavioral_rules>
- Review for: correctness, security, performance, and readability (in that order)
- Flag async anti-patterns: blocking calls in async context, missing await, 
  connection pool exhaustion
- When unsure about intent, state the assumption and proceed with the review
- Never suggest type: ignore without explaining what specific issue it suppresses
</behavioral_rules>

<output_format>
For each file reviewed, provide:
1. Summary (1 sentence: overall assessment)
2. Issues (severity-ordered table)
3. Suggested changes (diff format)
</output_format>
```

**Why this works:** Instead of trying to be everything, the prompt defines a specific expert with clear behavioral rules, action bias, and output structure.

---

## Example 3: Missing Examples → Few-Shot Classification

**Prompt Type:** User/task prompt
**Primary Issues:** Missing examples, no output format, implicit assumptions
**Techniques Applied:** Few-shot examples, output control, structure

### Before

```
Categorize these customer support tickets by urgency and department.
```

### After

```xml
<instructions>
Categorize each support ticket by urgency and department.

Urgency levels:
- P0: System down, data loss, security breach — immediate response
- P1: Major feature broken, blocking multiple users — same-day response
- P2: Minor bug, workaround exists — next business day
- P3: Feature request, documentation, cosmetic — backlog

Departments: ENGINEERING, BILLING, ACCOUNT, ONBOARDING
</instructions>

<examples>
<example>
<ticket>I can't log in and the password reset email never arrives. I have a demo with a customer in 30 minutes.</ticket>
<classification>
Urgency: P1
Department: ENGINEERING
Reason: Auth system failure blocking user with time-sensitive need
</classification>
</example>

<example>
<ticket>The export button generates a CSV but the date column is formatted wrong. I can fix it in Excel for now.</ticket>
<classification>
Urgency: P2
Department: ENGINEERING
Reason: Bug with workaround available, no business-critical impact
</classification>
</example>

<example>
<ticket>We were charged twice for March. Please refund the duplicate payment.</ticket>
<classification>
Urgency: P1
Department: BILLING
Reason: Financial error requiring same-day resolution
</classification>
</example>
</examples>

<tickets>
{tickets_to_classify}
</tickets>
```

**Why this works:** The examples define the classification scheme through demonstration, including the reasoning format. The model matches the pattern rather than inventing its own interpretation.

---

## Example 4: Flat Agent Instruction → Structured Context Engineering

**Prompt Type:** Agent instruction
**Primary Issues:** Flat structure, context flooding, no reasoning scaffolding
**Techniques Applied:** Structure, context engineering, reasoning, tool descriptions

### Before

```
You are a research assistant. Search the web for information about the topic 
the user asks about. Compile your findings into a report. Make sure the 
information is accurate and well-organized. Use multiple sources.
```

### After

```xml
<identity>
Research analyst producing evidence-based briefings. Optimize for accuracy 
over speed. Every claim must trace to a source.
</identity>

<process>
For each research query:

1. SCOPE: Identify 3-5 specific sub-questions that, answered together, fully 
   address the query. List them before searching.

2. SEARCH: For each sub-question, search using varied queries (different 
   phrasings, including technical terms and common terms). Aim for 3+ 
   independent sources per sub-question.

3. SYNTHESIZE: Cross-reference findings across sources. Flag contradictions 
   explicitly. Weight recent sources higher for fast-moving topics.

4. REPORT: Structure findings as specified in output_format.
</process>

<quality_rules>
- If fewer than 2 independent sources support a claim, mark it as [LOW CONFIDENCE]
- If sources contradict, present both positions with source attribution
- Never present search snippets as findings — read the full source page
- State "Insufficient evidence found" rather than speculating
</quality_rules>

<output_format>
## [Topic]: Research Briefing

### Key Findings
- [Finding 1] — [Source 1], [Source 2]
- [Finding 2] — [Source 1], [Source 3]

### Contradictions / Open Questions
- [Where sources disagree or evidence is insufficient]

### Sources
1. [Title] — [URL] — [Date] — [Relevance: HIGH/MEDIUM]
</output_format>
```

**Why this works:** The agent has a clear process (not just a goal), quality rules that prevent common failure modes, and an output format that enforces source tracing.

---

## Example 5: Weak Tool Description → Precise Tool Schema

**Prompt Type:** Tool description
**Primary Issues:** Vague delegation, missing boundary definition, no examples
**Techniques Applied:** Tool description engineering, specificity, boundary definition

### Before

```json
{
  "name": "search_files",
  "description": "Search for files in the project"
}
```

### After

```json
{
  "name": "search_files",
  "description": "Search for files in the project by name pattern (glob) or content pattern (regex). Use this tool when you need to find files by name (e.g., '**/*.py' for all Python files) or locate files containing specific code patterns (e.g., 'def process_' to find processing functions). Returns file paths sorted by modification time, most recent first. Does NOT read file contents — use read_file after locating the target. For searching within a known file, use search_in_file instead.",
  "parameters": {
    "pattern": {
      "type": "string",
      "description": "Glob pattern for name search (e.g., 'src/**/*.ts') OR regex for content search (e.g., 'class.*Handler'). The type parameter determines interpretation."
    },
    "type": {
      "type": "string",
      "enum": ["name", "content"],
      "description": "Whether 'pattern' is a file name glob or a content regex. Default: 'name'."
    },
    "path": {
      "type": "string",
      "description": "Directory to search within. Relative to project root. Default: '.' (entire project). Use to narrow scope when you know the general location."
    }
  }
}
```

**Why this works:** The description explains when to use the tool, when NOT to use it (boundary with other tools), what it returns, and provides concrete pattern examples. The model makes better tool selection decisions with this level of detail.

---

## Example 6: Simple Prompt That Should Stay Simple

**Prompt Type:** User/task prompt
**Primary Issues:** None — this is a counter-example showing when NOT to over-engineer

### The Prompt (Already Good)

```
Translate this English text to French. Maintain the same tone and formality level.

Text: "We're excited to announce that our new API is now available in beta."
```

### Why This Doesn't Need Improvement

- Task is simple and unambiguous
- Output format is obvious (French text)
- Single clear objective
- No edge cases to handle
- Adding XML tags, examples, or chain-of-thought would be over-engineering

**The lesson:** Not every prompt needs the full treatment. Match complexity of the prompt to complexity of the task. A simple task with a clear prompt should stay simple.
