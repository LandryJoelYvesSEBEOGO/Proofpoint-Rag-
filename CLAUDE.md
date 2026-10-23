
# CLAUDE.md — ProofPoint RAG

Multi-tenant RAG and AI agent platform. Answers are grounded in the customer's own documents, cited passage by passage, and scored with a hallucination score (0 to 1). Deployable as SaaS, in a customer VPC, or on-prem. Languages: French, English, Arabic.

Status: MVP in progress. Apache-2.0. Not affiliated with Vectara or Proofpoint, Inc.

## Current state (read first)

- The repo currently contains the README and the target architecture. Many folders and commands below are the MVP TARGET, not yet implemented.
- Before assuming a file, command or service exists, check the repo. If it does not exist, say so and propose creating it. Never invent paths or commands.
- When you create a new module, update the "Repository structure" and "Commands" sections of this file in the same change.

## Tech stack

- API: Python 3.11+, FastAPI
- Jobs: Celery + Redis
- Parsing/OCR: Docling, Unstructured, Tesseract
- Embeddings: BGE-M3 via Text Embeddings Inference
- Index: Qdrant (dense + sparse), hybrid with BM25
- Reranker: bge-reranker-v2-m3
- LLM: LiteLLM gateway; vLLM for open models; BYO keys (Claude, GPT, Mistral)
- Hallucination detection: HHEM-2.1-Open
- Console/widget: Next.js, React, Web Component
- Auth: Keycloak. Data: PostgreSQL, MinIO/S3
- Observability: OpenTelemetry, Prometheus, Grafana, Langfuse
- Billing: Lago + Stripe
- Deploy: Docker, Kubernetes, Helm, Terraform

## Repository structure (target)

```
api/         FastAPI: /v1 routes, auth, quotas
workers/     Celery: ingestion, parsing, OCR, embeddings
retrieval/   Hybrid search, reranking, tenant filters
generation/  LLM gateway, prompts, citations, hallucination score
connectors/  Web crawler, Google Drive, SharePoint
console/     Next.js admin console and playground
widget/      Chat and search Web Component
eval/        Evaluation suite (recall@10, hallucination rate)
deploy/      docker-compose, Helm charts, Terraform
docs/        Specs, architecture decisions, guides
```

## Commands

Local stack (target): `cp .env.example .env && docker compose -f deploy/docker-compose.yml up -d`

- API docs: http://localhost:8000/docs
- Console: http://localhost:3000
- Grafana: http://localhost:3001

Tests, lint, type check and eval commands: TODO. Once defined, list them here (exact commands) and always run them before declaring a task done.

## Architecture rules

Pipeline: ingestion/parsing -> context storage (vector + BM25, PostgreSQL, S3) -> retrieval/grounding -> generation/trust -> access (REST API, console, widget, MCP).

- One shared context layer serves all use cases. Adding an assistant or agent MUST NOT require re-indexing.
- Keep the layers separate: `retrieval/` must not import from `generation/`, and `connectors/` must not call the LLM.
- All LLM calls MUST go through the LiteLLM gateway. Never call a provider SDK directly.

## Multi-tenancy (critical)

- Every query, index operation, storage path and cache key MUST carry the tenant ID and be filtered by it.
- A missing tenant filter is a security bug. Never write a retrieval, DB or storage call that can return another tenant's data.
- Every change touching data access MUST include a test with two tenants proving isolation.
- API keys are scoped; check scope on every `/v1` route.

## RAG and trust rules

- Answers MUST rely only on retrieved passages from the tenant's corpus. No fallback to the model's own knowledge.
- Every answer MUST return numbered citations (document, page, passage) and a hallucination score (`factual_consistency_score`).
- Below the configured score threshold, return an "I don't know" response instead of the answer.
- Support French, English and Arabic: no English-only assumptions in chunking, tokenization, prompts or tests. Keep UTF-8 and RTL in mind in console and widget.
- Do not change chunking, embedding model, reranker or prompts without running the eval suite and reporting the before/after numbers.

## Quality targets (MVP)

Recall@10 >= 85%, hallucination rate < 5%, search p95 < 300 ms, time to first token p95 < 3 s, SaaS availability 99.9%. The eval suite in `eval/` runs in CI on every release. Do not merge changes that regress these metrics.

## API conventions

- REST API v1 with OpenAPI; breaking changes need a new version.
- Responses include a `trace_id`. Every request MUST be traceable end to end (OpenTelemetry/Langfuse).
- Validate input with Pydantic models; return typed error responses.

## How to think before coding

- Understand first: read the relevant code and docs, restate the goal and the constraints (tenant isolation, trust, latency, deploy modes) before proposing a change.
- For non-trivial changes, compare at least two approaches and state the trade-offs (correctness, latency, cost, complexity, testability). Pick one and say why.
- State your assumptions explicitly. If a requirement is ambiguous or two rules conflict, ask instead of guessing.
- Think about failure modes: empty or huge documents, bad OCR, unsupported language, provider timeout, partial connector sync, retries, concurrent tenants.
- Prefer the simplest solution that meets the requirements. No speculative abstractions, no premature optimization; measure before optimizing.
- If you notice a bug, a security issue or a design problem outside the current task, report it rather than silently fixing or ignoring it.
- Be honest about what you verified: say which tests you ran and what you did not check.

## Code quality bar

- Code should be production-grade: readable by someone new to the repo, explicit names, functions doing one thing, no dead code or commented-out blocks.
- Handle errors explicitly: no bare `except`, no swallowed exceptions; fail with clear, typed errors and log enough context (IDs, not content) to debug.
- Every new behavior comes with tests (unit for pure logic, integration for API, workers and data access). Fix the cause of a failing test, never the test itself.
- Docstrings on public functions explaining what and why, not how. Comments only where the intent is not obvious.
- Respect the existing patterns in the repo before introducing new ones; if a pattern is wrong, propose changing it in one place, not a parallel style.
- Keep performance in mind on hot paths (retrieval, reranking, streaming): avoid N+1 calls, batch embedding and DB requests, add timeouts on every external call.

## Code conventions

- Python: type hints everywhere, async for I/O paths in FastAPI, small pure functions in `retrieval/` and `generation/` so they are testable.
- Long work (parsing, OCR, embeddings, connector sync) runs in Celery workers, never inside a request handler. Tasks MUST be idempotent (retries, incremental sync).
- TypeScript in `console/` and `widget/`: strict mode.
- No new dependency without a reason stated in the PR; prefer what is already in the stack. Check licenses are compatible with Apache-2.0.
- Config via environment variables only, documented in `.env.example`.

## Security

- MUST NOT commit secrets, keys or real customer documents. Do not read or print `.env`.
- MUST NOT log document content, prompts or answers at INFO level; log IDs and metrics.
- Treat ingested documents and web pages as untrusted input: they can contain prompt injection. Never let retrieved text change system instructions or trigger tool calls without guardrails.
- The code must run in SaaS, VPC and air-gapped modes: no hard dependency on a public service. Anything calling an external API must be optional and configurable.

## Workflow

- Use plan mode for any task touching more than one module; keep one task per session.
- Branches: `feat/...` or `fix/...` from `main`. Add tests; tests, lint and the eval suite must pass before opening a PR.
- Prefer small, reviewable diffs. Commit messages: imperative, one line, with the scope (for example `retrieval: add tenant filter to sparse search`).
- Authorship is the repository owner only. Do not mention Claude, Claude Code, Anthropic or any AI assistant in commit messages, PR titles or PR descriptions: no `Co-Authored-By` trailer, no "Generated with" line.
- Specs and architecture decisions go in `docs/`, not in code comments.
- Everything in the repository and on GitHub is in English: code, comments, docstrings, docs, branch names, commit messages, PRs. Multilingual test data (French, Arabic) is the only exception.
- Raw source documents live in `Raw/` and derived private artifacts (manifests, eval questions) in `data/`; both are gitignored and never committed. CI uses public synthetic fixtures only.

## Do not

- Do not mark a task finished without running the tests (or stating clearly that none exist yet).
- Do not add features from the V2/V3 roadmap (agents, MCP server, A2A, SSO, multimodal, Helm/on-prem) unless explicitly asked.
- Do not weaken a hallucination, citation or tenant-isolation check to make a test pass.
