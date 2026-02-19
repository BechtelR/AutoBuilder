# External Providers

**Single source of truth for all external service providers used by AutoBuilder.**

Update this file when models change, new providers are added, or pricing shifts.

## LLM Providers

---

## Provider: Anthropic (Primary)

| Model | LiteLLM String | Input $/1M | Output $/1M | Context | Strengths |
|-------|---------------|-----------|-------------|---------|-----------|
| Claude Opus 4.6 | `anthropic/claude-opus-4-6` | $15.00 | $75.00 | 200K | Strongest reasoning, complex planning |
| Claude Sonnet 4.5 | `anthropic/claude-sonnet-4-6` | $3.00 | $15.00 | 200K | Best code generation, strong review |
| Claude Haiku 4.5 | `anthropic/claude-haiku-4-5-20251001` | $0.80 | $4.00 | 200K | Fast classification, summarization |

## Provider: OpenAI (Fallback)

| Model | LiteLLM String | Input $/1M | Output $/1M | Context | Strengths |
|-------|---------------|-----------|-------------|---------|-----------|
| GPT-5.2 | `openai/gpt-5.2` | $1.75 | $14.00 | 400K | Complex reasoning, SWE-bench 80% |
| GPT-5 | `openai/gpt-5` | $1.25 | $10.00 | 400K | Standard coding |
| GPT-5 Mini | `openai/gpt-5-mini` | $0.25 | $2.00 | 400K | Mid-tier, cost-effective |
| GPT-5 Nano | `openai/gpt-5-nano` | $0.05 | $0.40 | 400K | Classification, cheap bulk |

## Provider: Google (Fallback)

| Model | LiteLLM String | Input $/1M | Output $/1M | Context | Strengths |
|-------|---------------|-----------|-------------|---------|-----------|
| Gemini 2.5 Pro | `gemini/gemini-2.5-pro` | $1.25 | $10.00 | 1M | Large context, stable production |
| Gemini 3 Flash Preview | `gemini/gemini-3-flash-preview` | $0.50 | $3.00 | 1M | Fast, good code |
| Gemini 2.5 Flash | `gemini/gemini-2.5-flash` | $0.30 | $2.50 | 1M | Cost-effective |
| Gemini 2.5 Flash-Lite | `gemini/gemini-2.5-flash-lite` | $0.10 | $0.40 | 1M | Cheapest, classification |

---

## AutoBuilder Task Mapping

Default model assignments by task type. Configured via `AUTOBUILDER_DEFAULT_*_MODEL` env vars.

| Task Type | Default Model | Env Var | Rationale |
|-----------|---------------|---------|-----------|
| Planning | `anthropic/claude-opus-4-6` | `AUTOBUILDER_DEFAULT_PLAN_MODEL` | Benefits from strongest reasoning |
| Code Implementation | `anthropic/claude-sonnet-4-6` | `AUTOBUILDER_DEFAULT_CODE_MODEL` | Best code generation |
| Review | `anthropic/claude-sonnet-4-6` | `AUTOBUILDER_DEFAULT_REVIEW_MODEL` | Strong analytical capability |
| Classification / Summarization | `anthropic/claude-haiku-4-5-20251001` | `AUTOBUILDER_DEFAULT_FAST_MODEL` | Fast, cost-effective |

### Complexity Escalation

The LLM Router can escalate based on task complexity:

| Task Type | Standard | Complex |
|-----------|----------|---------|
| Code Implementation | Sonnet 4.5 | Opus 4.6 |
| Review | Sonnet 4.5 | Opus 4.6 |
| Planning | Opus 4.6 | Opus 4.6 |

---

## Fallback Chains

When the primary model is unavailable or rate-limited, the router walks the fallback chain. Resolution: user override > fallback chain > system default.

| Tier | Primary (Anthropic) | Fallback 1 (OpenAI) | Fallback 2 (Google) |
|------|--------------------|--------------------|-------------------|
| Strongest reasoning | `anthropic/claude-opus-4-6` | `openai/gpt-5.2` | `gemini/gemini-2.5-pro` |
| Standard coding | `anthropic/claude-sonnet-4-6` | `openai/gpt-5` | `gemini/gemini-2.5-pro` |
| Fast/cheap | `anthropic/claude-haiku-4-5-20251001` | `openai/gpt-5-nano` | `gemini/gemini-2.5-flash-lite` |

---

## Environment Variables

```bash
# Primary model defaults (AUTOBUILDER_ prefix via pydantic-settings)
AUTOBUILDER_DEFAULT_CODE_MODEL=anthropic/claude-sonnet-4-6
AUTOBUILDER_DEFAULT_PLAN_MODEL=anthropic/claude-opus-4-6
AUTOBUILDER_DEFAULT_REVIEW_MODEL=anthropic/claude-sonnet-4-6
AUTOBUILDER_DEFAULT_FAST_MODEL=anthropic/claude-haiku-4-5-20251001

# API keys (no prefix — provider standard)
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

Fallback chains are configured in the routing config (code), not env vars. Env vars set the primary defaults only.

---

*Last Updated: 2026-02-14*
*Pricing as of: February 2026*
