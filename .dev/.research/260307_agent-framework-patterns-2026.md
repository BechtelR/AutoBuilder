# Agent Framework Patterns Research - March 2026

Research date: 2026-03-07
Focus: Dynamic/Composable System Prompts + Composable/Dynamic Agent Assembly

---

## Part 1: Dynamic/Composable System Prompts

### 1.1 OpenAI Agents SDK - Dynamic Instructions

**Pattern**: Instructions-as-function

**How it works**: The `Agent` class accepts `instructions` as either a static string OR a callable `(agent, context) -> str`. At runtime, the SDK calls the function before each LLM invocation, allowing the system prompt to adapt based on task context, user state, or runtime signals. OpenAI's practical guide recommends a single flexible base prompt with policy variables over maintaining numerous individual prompts.

```python
# Pseudo-pattern (from OpenAI docs)
def dynamic_instructions(agent, context):
    role_section = load_role(context.user)
    policy = load_policy(context.task_type)
    return f"{role_section}\n{policy}\n{base_instructions}"

agent = Agent(name="support", instructions=dynamic_instructions, tools=[...])
```

**Pros**:
- Dead simple API -- one function, full control
- No new abstractions to learn
- Context object gives access to full runtime state

**Cons**:
- No built-in composition/fragment management
- No versioning or A/B testing of prompt variants
- Prompt logic lives in code, not config

**Relevance to AutoBuilder**: HIGH. This is the minimal viable pattern. Our Director/PM/Worker agents could each use a dynamic instructions function that assembles prompts from project context, skill definitions, and role-specific sections. Maps directly to ADK's agent construction.

---

### 1.2 SPEAR - Prompts as First-Class Citizens

**Pattern**: Executable prompt algebra with runtime refinement

**How it works**: Academic framework (VLDB/CIDR 2026) that promotes prompts to first-class entities with formal algebra. Prompts are structured programs that support: (1) composition operators (combine fragments), (2) runtime refinement (modify prompts based on confidence/latency/missing context signals), and (3) versioned views with introspection and logging. A `ref_log` tracks each refinement with runtime signals (confidence scores, token usage, latency) enabling cost-based planning over which refiners to apply.

**Pros**:
- Rigorous formal model for prompt optimization
- Cost-aware prompt adaptation (skip low-impact refinements)
- Full audit trail of prompt evolution

**Cons**:
- Academic -- no production-ready implementation
- Heavyweight for most use cases
- Over-engineered for early-stage systems

**Relevance to AutoBuilder**: LOW for implementation, HIGH for inspiration. The idea of prompt fragments with composition operators and runtime refinement signals is worth borrowing conceptually. The cost-based planning over refinements could inform future optimization.

---

### 1.3 Modular Prompt Engineering - Fragment-Based Assembly

**Pattern**: Prompt fragments as composable LEGO blocks

**How it works**: Industry-wide pattern (not framework-specific) where prompts are decomposed into typed fragments: Role/Persona, Task Logic, Output Format, Guardrails, Context. Fragments are maintained independently, versioned, and assembled programmatically per invocation. Red Hat's approach distinguishes "big prompts" (monolithic, all context upfront) vs "small prompts" (minimal, dynamically extended via tool use and progressive disclosure).

Fragment types:
- **Role/Persona**: Identity, expertise level, behavioral constraints
- **Task Logic**: Reasoning approach (CoT, ReAct, etc.)
- **Output Format**: JSON schemas, structured outputs
- **Guardrails**: Safety, scope limitations
- **Context**: Project-specific data, retrieved knowledge

**Pros**:
- 13x faster iteration reported vs monolithic prompts
- Single fragment update improves all prompts using it
- Easy to test individual fragments
- Scales across teams and projects

**Cons**:
- No standard format (everyone rolls their own)
- Fragment interaction/ordering effects are subtle
- Requires tooling for assembly and testing

**Relevance to AutoBuilder**: HIGH. This maps directly to our hierarchical agent design. Director, PM, and Worker agents each need different fragment combinations. Project context, skill instructions, and role definitions are natural fragment boundaries.

---

### 1.4 DSPy - Programmatic Prompt Optimization

**Pattern**: Signatures + Optimizers (no manual prompts)

**How it works**: DSPy eliminates manual prompt writing entirely. You define Signatures (input/output specs like `"question -> answer"`) and Modules (strategies for invoking LLMs). Optimizers (MIPROv2, COPRO) automatically find optimal instructions and few-shot examples using Bayesian optimization against a metric function and training set. The developer never writes a system prompt -- the optimizer generates one.

**Pros**:
- Removes prompt engineering entirely
- Optimizes for measurable outcomes
- Model-agnostic (prompt adapts per model)

**Cons**:
- Requires training data and metrics
- Opaque -- hard to understand/debug generated prompts
- Overhead of optimization loop
- Not designed for multi-agent orchestration

**Relevance to AutoBuilder**: LOW for direct adoption (our agents need interpretable, auditable prompts), MEDIUM for specific sub-tasks where we could auto-optimize tool-use prompts or output format instructions.

---

### 1.5 Semantic Kernel / Microsoft Agent Framework - YAML Prompt Templates

**Pattern**: YAML-defined prompt templates with semantic functions

**How it works**: Prompts defined as YAML files with metadata (description, input variables, model parameters, execution settings). Templates use Handlebars-style variable interpolation. The framework loads and renders templates at runtime, injecting context variables. Separates prompt definition from code entirely.

```yaml
# Semantic Kernel YAML prompt schema
name: summarize
description: Summarize a document
template: |
  You are a {{role}} specialist.
  Summarize the following: {{$input}}
  Format: {{output_format}}
template_format: handlebars
input_variables:
  - name: role
  - name: output_format
    default: bullet_points
execution_settings:
  default:
    max_tokens: 500
    temperature: 0.3
```

**Pros**:
- Clean separation of concerns
- Non-engineers can modify prompts
- Version control friendly
- Supports inline comments (YAML > JSON for this)

**Cons**:
- Limited composition -- templates are flat
- No runtime adaptation beyond variable substitution
- Tied to Microsoft's ecosystem patterns

**Relevance to AutoBuilder**: MEDIUM. The YAML template pattern is clean for static prompts but lacks the dynamism we need for context-aware agent behavior. Could work for tool/skill instruction templates.

---

### 1.6 Agent Skills Progressive Disclosure (Anthropic Standard)

**Pattern**: On-demand prompt extension via skill loading

**How it works**: Agents start with a minimal system prompt. When a user request matches a skill's domain, only that skill's instructions are loaded into context. Each skill is a folder with a SKILL.md containing metadata and instructions. This solves the "prompt bloat" problem -- instead of frontloading all possible instructions, agents discover and load capabilities progressively.

**Pros**:
- Solves token cost explosion
- Keeps base prompts clean and focused
- Skills are portable across agents/frameworks
- Open standard with broad adoption

**Cons**:
- Skill matching/discovery adds latency
- Skill interactions can conflict
- No formal composition model between skills

**Relevance to AutoBuilder**: CRITICAL. We already plan to use Agent Skills (Decision #37). Progressive disclosure is the right pattern for our Worker agents -- load skill instructions only when executing relevant deliverables.

---

### Summary: Recommended Approach for AutoBuilder

**Hybrid pattern combining three layers:**

1. **Base layer**: Static role/persona fragments per agent type (Director, PM, Worker) -- version-controlled YAML or Python constants
2. **Context layer**: Dynamic instructions function (OpenAI pattern) that assembles base + project context + active task context at runtime
3. **Skill layer**: Progressive disclosure (Anthropic Agent Skills) that loads domain-specific instructions on demand

This avoids both the "mega-prompt" anti-pattern and the over-engineering of formal prompt algebras.

---

## Part 2: Composable/Dynamic Agent Assembly

### 2.1 Google ADK - Agent Tree with Workflow Agents

**Pattern**: Hierarchical agent tree with typed workflow nodes

**How it works**: ADK composes agents into a tree where parent agents contain sub-agents. Three built-in workflow agent types provide deterministic composition: SequentialAgent, ParallelAgent, LoopAgent. LlmAgent instances provide dynamic routing via `transfer_to_agent` tool calls. CustomAgent enables arbitrary orchestration logic. The runtime is an event loop yielding Event streams.

```python
# ADK composition pattern
director = LlmAgent(name="director", sub_agents=[pm_agent])
pm_agent = LlmAgent(name="pm", sub_agents=[
    SequentialAgent(name="pipeline", sub_agents=[
        planner,
        ParallelAgent(name="workers", sub_agents=[worker1, worker2]),
        reviewer,
    ])
])
```

**Pros**:
- Native to our stack
- Event-driven (yields Events, not returns)
- Workflow agents give deterministic control where needed
- CustomAgent escape hatch for complex orchestration

**Cons**:
- Agent tree is typically static (built at init time)
- No built-in agent registry or discovery
- Sub-agent list is set at construction
- Limited runtime graph modification

**Relevance to AutoBuilder**: CRITICAL. This IS our framework. The key gap is that ADK agent trees are static -- we need a pattern for dynamic sub-agent construction per project/task.

---

### 2.2 OpenAI Agents SDK - Handoffs + Agent-as-Tool

**Pattern**: Two composition primitives: handoff (sequential delegation) and agent-as-tool (hierarchical delegation)

**How it works**: Handoffs transfer control from one agent to another (like passing a baton -- the original agent stops). Agent-as-tool runs a sub-agent as a tool call (like asking for help -- the original agent gets the result back and continues). Handoffs can be dynamically enabled/disabled at runtime via `is_enabled` function. Agents are lightweight Python objects with name, instructions, tools, and handoffs.

```python
# Two composition modes
triage = Agent(
    name="triage",
    handoffs=[refund_agent, billing_agent],  # sequential delegation
    tools=[Agent.as_tool(lookup_agent)],      # hierarchical delegation
)
```

**Pros**:
- Two primitives cover most multi-agent patterns
- Runtime enable/disable of handoffs
- Agents are cheap to create (just config objects)
- Clean mental model

**Cons**:
- Flat composition (no deep hierarchies natively)
- No workflow agents (sequential/parallel/loop)
- No persistent agent state between invocations
- Tied to OpenAI models

**Relevance to AutoBuilder**: MEDIUM. The handoff vs agent-as-tool distinction is a useful mental model. ADK's `transfer_to_agent` is equivalent to handoffs. We could adopt the agent-as-tool pattern for cases where a parent agent needs a sub-agent's result without losing control.

---

### 2.3 CrewAI - Declarative Role-Based Crews

**Pattern**: Agent-as-config with role/goal/backstory + task assignment

**How it works**: Agents are defined declaratively with role, goal, and backstory strings. Tasks define what needs to be done, and a Crew orchestrates assignment. Two modes: Crews (autonomous, agents have agency) and Flows (event-driven pipelines, more predictable). Crew composition is declarative -- you define agents and tasks, the framework handles orchestration.

```python
# CrewAI declarative pattern
researcher = Agent(role="Senior Researcher", goal="Find accurate data", backstory="...")
writer = Agent(role="Technical Writer", goal="Create clear docs", backstory="...")
crew = Crew(agents=[researcher, writer], tasks=[research_task, write_task])
```

**Pros**:
- Extremely readable and intuitive
- Natural mapping to team metaphors
- Crews vs Flows gives flexibility
- Easy to explain to non-engineers

**Cons**:
- Role/goal/backstory is a weak abstraction for complex behaviors
- Limited control over execution flow
- Implicit orchestration can be unpredictable
- Not suited for deep hierarchies

**Relevance to AutoBuilder**: LOW for direct adoption (too high-level for our needs), but the declarative agent definition pattern (agent-as-config) is worth borrowing for our agent registry.

---

### 2.4 LangGraph - Directed Graph with Dynamic Nodes

**Pattern**: State machine with runtime graph mutation

**How it works**: Workflows are directed graphs where nodes are functions/agents and edges define control flow. State is centralized and shared across all nodes. The Send API enables dynamic node creation at runtime -- an orchestrator node can spawn arbitrary worker nodes with specific inputs. Conditional edges enable dynamic routing. Full serialization supports replay and debugging.

**Key capability**: Dynamic worker spawning via Send API:
```python
# LangGraph dynamic composition
def orchestrator(state):
    # Dynamically create workers based on state
    return [Send("worker", {"task": t}) for t in state["tasks"]]

graph.add_conditional_edges("orchestrator", orchestrator)
```

**Pros**:
- True runtime graph mutation
- Send API enables dynamic parallelism
- Full state serialization and replay
- Maximum control over execution flow
- YAML-based graph definition also supported

**Cons**:
- Steep learning curve
- Verbose for simple cases
- Graph debugging can be complex
- Centralized state can become a bottleneck

**Relevance to AutoBuilder**: HIGH for the Send API pattern. Our PM agent needs to dynamically spawn Worker agents based on deliverable decomposition. LangGraph's approach of "orchestrator decides at runtime how many workers to create and what to send them" maps exactly to our use case. We need to replicate this in ADK.

---

### 2.5 Semantic Kernel - Orchestration Patterns + Agent Framework

**Pattern**: Named orchestration patterns as first-class abstractions

**How it works**: Microsoft unified Semantic Kernel + AutoGen into a single Agent Framework (RC status, Q1 2026 GA target). Provides named orchestration patterns: Sequential, Concurrent, GroupChat, Handoff, and Magnetic (agents declare what they can handle, framework routes dynamically). Agents are composable building blocks that plug into any orchestration pattern.

**Magnetic orchestration** is notable: agents declare capabilities, and the framework dynamically routes tasks to capable agents without explicit wiring.

**Pros**:
- Named patterns reduce decision fatigue
- Magnetic orchestration is a novel capability-based routing pattern
- Production-grade (enterprise-focused)
- Cross-language (Python + .NET)

**Cons**:
- Heavy framework (enterprise overhead)
- Microsoft ecosystem gravity
- Pattern selection still requires expertise
- Complex configuration

**Relevance to AutoBuilder**: MEDIUM. The "Magnetic" orchestration pattern (capability-based routing) is interesting for our skill-to-agent matching. When a deliverable requires specific skills, we could route to agents that have those skills loaded.

---

### 2.6 Anthropic Agent Skills + Registries Ecosystem

**Pattern**: Skill-based agent capability extension with marketplace distribution

**How it works**: Agent Skills (open standard, Dec 2025) are folder-based packages containing SKILL.md + supporting files. Agents discover skills via filesystem scanning or registry lookup. Multiple registries/marketplaces have emerged: SkillsMP, agentskill.sh (44k+ skills), skills.sh, Skillstore. Spring AI packages skills as JARs distributable via Maven. pydantic-ai-skills provides type-safe skill loading with progressive disclosure.

Adopted by: Microsoft, OpenAI, Atlassian, Figma, Cursor, GitHub.

**Skill structure**:
```
skills/
  web-research/
    SKILL.md          # Metadata + instructions
    search_patterns.md # Supporting reference
    templates/         # Prompt templates
```

**Pros**:
- Open standard with massive adoption
- Progressive disclosure solves token bloat
- Portable across frameworks
- Growing ecosystem of pre-built skills

**Cons**:
- Skills are instruction-only (no executable code in spec)
- No formal skill composition/dependency model
- Quality varies wildly in marketplaces
- Skill conflicts not addressed by spec

**Relevance to AutoBuilder**: CRITICAL. We already decided on Agent Skills (Decision #37). The ecosystem validation is strong. Key insight: skills extend agent PROMPTS (instructions), not agent CODE. Our implementation should treat skills as composable prompt fragments that get loaded into the context layer.

---

### 2.7 pydantic-ai-skills - Type-Safe Skill Loading

**Pattern**: Skills as Pydantic AI Toolsets with progressive disclosure

**How it works**: Wraps the Agent Skills standard in a Pydantic AI Toolset interface. Skills are discovered from filesystem, validated with type hints, and loaded progressively. Integrates as a standard tool -- agents can "list skills" and "load skill" as tool calls. Built on Python dataclasses with full type safety.

**Pros**:
- Type-safe skill loading
- Drop-in integration (standard Toolset interface)
- Filesystem and programmatic skill sources
- Minimal dependencies

**Cons**:
- Pydantic AI specific
- Thin wrapper (not much beyond the standard)

**Relevance to AutoBuilder**: MEDIUM. We use ADK not Pydantic AI, but the pattern of "skills as a tool that agents can discover and load" is exactly right. We should implement equivalent functionality in our ADK agent tools.

---

## Part 3: Claude Code System Prompt Architecture Analysis

Source: [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts)

Claude Code (Anthropic's CLI agent) uses **232 files** of conditional micro-fragments — not a monolithic system prompt. Analysis of the v2.1.70 prompt structure revealed production patterns directly applicable to AutoBuilder.

### Architecture

| Category | Count | Size | Loading Strategy |
|----------|-------|------|-----------------|
| System prompt fragments | ~60 | 67KB | **Always loaded** (base behavior) |
| Agent prompts | ~29 | 84KB | **Per subagent** (fresh context) |
| Skills | ~7 | 48KB | **On trigger** (progressive disclosure) |
| Data references | ~25 | 161KB | **On skill match** (skill-triggered cascade) |
| System reminders | ~50 | 25KB | **Conditionally injected** (event-driven) |
| Tool descriptions | ~90 | varies | **Per available tool** |

### Key Patterns Identified

**1. Micro-Fragment Granularity.** "Doing tasks" alone is 12 separate fragments: `avoid-over-engineering`, `no-premature-abstractions`, `no-unnecessary-additions`, `no-unnecessary-error-handling`, `no-compatibility-hacks`, `minimize-file-creation`, etc. Each is 1-5 sentences. Not all load every time — conditional inclusion based on context.

**2. System Reminders.** `<system-reminder>` tags injected into conversation as user-role messages, not part of the system prompt. Ephemeral nudges: token budget, file state changes, plan mode status, hook results. Don't inflate base prompt. Get compacted during context compression.

**3. Skill Cascade.** `skill-build-with-claude-api.md` detects project language, then instructs the agent to read specific `data-*` reference files. Two-stage progressive disclosure: match skill → skill routes to further data loads.

**4. Variable Contract.** Each fragment declares required variables in HTML comment metadata (`variables: [SKILL_TOOL_NAME, AGENT_TOOL_NAME]`). Simple string substitution, not a template engine.

**5. Subagent Context Model.** Two modes: omit `subagent_type` = agent inherits full conversation context (directive-style prompt); specify `subagent_type` = fresh context (briefing-style prompt with full background).

### What We Adopt vs. Reject

| Pattern | Adopt? | AutoBuilder Adaptation |
|---------|--------|----------------------|
| Micro-fragments, conditionally loaded | Yes | Named fragments in InstructionAssembler, role-keyed |
| System reminders (ephemeral nudges) | Yes | Soft nudges only (token budget, state changes). Hard governance in system prompt. |
| Skill cascade (skill → load references) | Yes | `metadata.cascades` field in skill frontmatter |
| Variable contract | Partial | Fragment function signatures serve this role |
| Subagent fresh vs inherited context | Yes | Worker = fresh (per-deliverable), PM = inherits project session |
| Defensive repetition (same point 4 ways) | No | Keep it DRY — one clear statement per constraint |
| Massive tool descriptions everywhere | No | Our tools are simpler; per-role vending already limits exposure |
| Monolithic data file loading | No | Skill cascading loads targeted references |

---

## Part 4: Synthesis and Recommendations for AutoBuilder

### Dynamic System Prompts - Recommended Architecture

```
+------------------------------------------+
|           Agent Invocation               |
+------------------------------------------+
|  1. Base Fragment (role/persona)         |  <- Static, version-controlled
|  2. Project Context Fragment             |  <- Dynamic, from DB/state
|  3. Task Context Fragment                |  <- Dynamic, from current job
|  4. Active Skills Instructions           |  <- Progressive disclosure
|  5. Output Format / Guardrails           |  <- Static per agent type
+------------------------------------------+
|  Assembled by: instructions_fn(agent, ctx)|
+------------------------------------------+
```

**Implementation**: Each ADK agent gets a factory function that accepts project/task context and returns assembled instructions. Fragments are stored as Python string constants or loaded from skill files. No YAML templates needed initially (YAGNI) -- graduate to YAML if/when non-engineers need to edit prompts.

### Dynamic Agent Assembly - Recommended Architecture

```
+-------------------+
|  Agent Registry   |  <- Maps agent_type + skills -> agent factory
+-------------------+
         |
    build_agent(type, skills, project_ctx)
         |
+-------------------+
| ADK Agent Tree    |  <- Constructed per job invocation
| Director          |
|   PM              |
|     Worker[0..N]  |  <- Dynamic count based on deliverables
+-------------------+
```

**Implementation**: An `AgentRegistry` maps agent types to factory functions. When a job starts, the PM determines deliverable count and the registry constructs the right number of Worker agents with appropriate skills loaded. This mirrors LangGraph's Send API pattern but within ADK's agent tree model.

### Key Design Decisions

1. **Instructions function over YAML templates** -- We need runtime dynamism, not just variable substitution. Python functions give us full control. Revisit YAML if prompt editing becomes a non-engineer workflow.

2. **Agent factory over static tree** -- ADK agent trees are built at construction time. We reconstruct the relevant subtree per job invocation. Agents are cheap to create.

3. **Progressive skill disclosure over mega-prompts** -- Load skill instructions only when a deliverable matches a skill domain. Keeps token costs manageable and prompts focused.

4. **Capability-based routing (inspired by Magnetic orchestration)** -- When skills declare what they handle, the PM can route deliverables to appropriately-skilled workers without hardcoded mapping.

5. **Fragment composition over prompt optimization** -- DSPy-style optimization is overkill for our use case. Manual fragment composition with clear boundaries is more debuggable and auditable.

---

## Sources

- [Agentic Design Patterns: The 2026 Guide](https://www.sitepoint.com/the-definitive-guide-to-agentic-design-patterns-in-2026/)
- [OpenAI Agents SDK - Agents Documentation](https://openai.github.io/openai-agents-python/agents/)
- [OpenAI Agents SDK - Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK Review 2026](https://agentlas.pro/frameworks/openai-agents-sdk/)
- [Building Production-Ready AI Agents with OpenAI Agent SDK](https://medium.com/@sausi/in-2026-building-ai-agents-isnt-about-prompts-it-s-about-architecture-15f5cfc93950)
- [A Practical Guide to Building Agents (OpenAI)](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Google ADK Multi-Agent Systems](https://google.github.io/adk-docs/agents/multi-agents/)
- [Google ADK Custom Agents](https://google.github.io/adk-docs/agents/custom-agents/)
- [Building Collaborative AI with ADK (Google Cloud Blog)](https://cloud.google.com/blog/topics/developers-practitioners/building-collaborative-ai-a-developers-guide-to-multi-agent-systems-with-adk)
- [SPEAR: Making Prompts First-Class Citizens (VLDB 2026)](https://vldb.org/cidrdb/papers/2026/p26-cetintemel.pdf)
- [DSPy Framework](https://dspy.ai/)
- [DSPy Programmatic Prompting Guide 2026](https://aitoolsinsights.com/articles/dspy-programmatic-prompting-guide)
- [Semantic Kernel Agent Orchestration](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/)
- [Semantic Kernel Multi-Agent Orchestration (DevBlog)](https://devblogs.microsoft.com/semantic-kernel/semantic-kernel-multi-agent-orchestration/)
- [Microsoft Agent Framework Convergence](https://visualstudiomagazine.com/articles/2025/10/01/semantic-kernel-autogen--open-source-microsoft-agent-framework.aspx)
- [LangGraph Agent Framework](https://www.langchain.com/langgraph)
- [LangGraph Explained 2026](https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3)
- [CrewAI vs LangGraph vs AutoGen vs OpenAgents 2026](https://openagents.org/blog/posts/2026-02-23-open-source-ai-agent-frameworks-compared)
- [Definitive Guide to Agentic Frameworks 2026](https://blog.softmaxdata.com/definitive-guide-to-agentic-frameworks-in-2026-langgraph-crewai-ag2-openai-and-more/)
- [Anthropic Agent Skills Announcement](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Agent Skills as Open Standard (The New Stack)](https://thenewstack.io/agent-skills-anthropics-next-bid-to-define-ai-standards/)
- [pydantic-ai-skills](https://pub.towardsai.net/introducing-pydantic-ai-skills-composable-agent-skills-for-the-pydantic-ai-ecosystem-dc98dd2bff53)
- [Spring AI Agent Skills](https://spring.io/blog/2026/01/13/spring-ai-generic-agent-skills/)
- [Agent Skills Registries & Collections 2026](https://medium.com/@frulouis/25-top-claude-agent-skills-registries-community-collections-you-should-know-2025-52aab45c877d)
- [Agent Skills Deep Dive (Addo Zhang)](https://addozhang.medium.com/agent-skills-deep-dive-building-a-reusable-skills-ecosystem-for-ai-agents-ccb1507b2c0f)
- [How System Prompts Define Agent Behavior](https://www.dbreunig.com/2026/02/10/system-prompts-define-the-agent-as-much-as-the-model.html)
- [Modular Prompt Engineering 2026](https://chatpromptgenius.com/modular-prompt-engineering-best-practices-for-2026/)
- [Prompt Engineering: Big vs Small Prompts (Red Hat)](https://developers.redhat.com/articles/2026/02/23/prompt-engineering-big-vs-small-prompts-ai-agents)
- [YAML Schema Reference for Prompts (Microsoft)](https://learn.microsoft.com/en-us/semantic-kernel/concepts/prompts/yaml-schema)
- [AI Agent Skills Complete Guide 2026](https://calmops.com/ai/ai-agent-skills-complete-guide-2026/)
- [Awesome Agent Skills (GitHub)](https://github.com/skillmatic-ai/awesome-agent-skills)
- [agentskills.io](https://agentskills.io/home)
- [Microsoft Agent Framework Custom Orchestration](https://tech.hub.ms/2026-03-02-Demystifying-Custom-Orchestration-in-Microsoft-Agent-Framework-Workflows.html)
