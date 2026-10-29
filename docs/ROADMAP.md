# ProofPoint RAG MVP roadmap

This document turns the source roadmap and requirements specification into a working plan: what each phase is for, what we will build, what evidence marks it complete, and what is currently known. It does not change the product scope or the acceptance targets in the source documents.

## How to use this roadmap

- Weeks are relative to the project start; no calendar start date has been agreed. The 26-week plan is an estimate, not a delivery commitment.
- Each phase ends with a gate. Do not mark a gate complete until its evidence exists and its acceptance checks pass.
- Status means **Done** only when there is implementation or a saved deliverable and verification. A decision to skip a gate is recorded as **Waived**, not Done.
- At each task update, record the phase and sprint, what changed, how it was verified, and any decision or blocker. Update this document when the evidence or status changes.
- Keep cloud-provider and region decisions explicit. Do not write provider-specific deployment configuration until those choices are made.
- Protect tenant boundaries at every data layer. Use public or synthetic test data in CI; never commit customer documents or derived private evaluation data.

## Current position — 2026-10-29

**Active: Phase 1, Sprint 1 — Infrastructure and accounts.**

The project chose to proceed without the Phase 0 market gate. The J0 requirement for three pilot letters of intent was explicitly waived as a sequencing decision. This does **not** mean that the letters, prospect interviews, evaluation set, or other Phase 0 deliverables have been completed.

| Sprint 1 item | Status | Evidence / remaining work |
|---|---|---|
| Local development services | Partial | Compose defines PostgreSQL, Valkey, SeaweedFS, and Qdrant with persistent volumes and healthchecks. An isolated validation stack started healthy; the regular project stack remains unverified. |
| FastAPI and OpenAPI skeleton | Partial | Health, OpenAPI, tracing, typed errors, and a Compose API service/healthcheck are present. Scoped API-key authentication and rate limits are not implemented. The API container image has not yet been built. |
| CI quality checks | Partial | Lint, formatting, typing, import contracts, and tests are configured in CI. There is no build-and-deploy pipeline for staging or production. |
| Staging/production infrastructure | Decision needed | Terraform/Kubernetes target is deferred until the hosting provider and region are chosen. |
| Backups and restore verification | Done for local development | On-demand archive and restore were exercised against isolated PostgreSQL, Valkey, SeaweedFS, and Qdrant volumes: test markers survived backup, mutation, and restore, and all four services returned healthy. Archives remain unencrypted and are not production backups. |
| Keycloak organizations and roles | Not started | Admin / Developer / Reader role management is not implemented. |

Latest recorded code checks: 35 tests passed with 100% coverage; Ruff, mypy, import contracts, and Compose configuration validation passed. The isolated stateful-service stack and backup/restore path were verified. The API image build and regular project stack have **not** been verified.

The team is partially constituted. The pilot sector and country were intentionally passed over; they remain undecided rather than completed.

## Free-first implementation policy

The project will use the user's proposed free or self-hosted options before considering paid services. “Free” means no planned subscription or usage charge; it does not guarantee availability, sufficient quotas, data residency, or zero incidental costs. Free-tier limits and terms can change, so verify them immediately before relying on a hosted service.

| Need | Default for this project | Optional free alternative | Limits and safeguards |
|---|---|---|---|
| Development and staging | Keep the current Docker Compose stack on the development machine. Use `kind`, k3s, or minikube locally only when Kubernetes behavior needs testing. | Oracle Cloud Always Free for a temporary online test. | Oracle capacity can be unavailable in a region and account verification requires a bank card. It is not the default and must be approved before provisioning. No production SLA is assumed. |
| Embeddings and reranking | Start on CPU locally; test TEI CPU or an ONNX/quantized option before deciding hardware needs. | Colab or Kaggle for offline batch experiments; Hugging Face's free API for small tests. | Free GPU quotas are limited and sessions can stop; notebooks are not stable inference services. Use only public or synthetic test data unless external processing of private documents is explicitly approved. |
| PostgreSQL, queue/cache, object store, vector search | Keep PostgreSQL, Valkey, SeaweedFS, and Qdrant in the existing Compose stack. | For isolated online experiments: Neon or Supabase (PostgreSQL), Upstash (Redis-compatible cache), Cloudflare R2 (object storage), and Qdrant Cloud free tier. | Quotas are limited; hosted databases may pause after inactivity. Qdrant Cloud's proposed 1 GB and R2's proposed 10 GB are planning figures from the user's suggestion, not guarantees—check current terms. Do not mix providers or move tenant data until the architecture, region, credentials, and isolation tests are reviewed. |
| Backups | Create on-demand offline archives of the local Compose data volumes; keep copies on a local external drive. | `pg_dump`, Qdrant snapshots, and `restic`/`rclone` to R2 or Backblaze B2. | The volume archive briefly stops stateful services and requires compatible Compose service versions to restore. Local archives are not encrypted; use only for development data until encryption is added. Remote storage may have limits or charges. A backup is not complete until restoration has been demonstrated. |
| CI/CD | Keep the existing GitHub Actions checks. Use `act` for local workflow iteration when useful. | GitHub Actions on the free allowance, or GitLab CI. | Private-repository minutes and artifact storage may be limited; monitor consumption. Avoid unnecessary large image builds. |
| Identity and processing tools | Prefer the existing self-hosted/open-source choices: Keycloak, Docling/OCR, and Celery. | Authentik or Supabase Auth for a development-only experiment if Keycloak is too costly to operate locally. | These still consume compute and memory. Do not replace the target identity design or use hosted auth for real tenants without an explicit decision and security review. |
| Engineering capacity | Keep the team-size/capacity gap visible; the planned six human roles cannot be replaced by free software. | Free AI coding assistants and community contributors can help with bounded tasks. | Tools do not replace accountable engineering, review, operations, or security ownership. Do not send private source documents, secrets, or customer data to an assistant. |

### Operating rules

1. Do not create a paid subscription, provision a cloud resource, enter payment details, or incur usage charges without the user's explicit approval.
2. Keep the local Compose stack as the source of truth for Phase 1 development. Treat hosted free tiers as disposable experiments, not production foundations.
3. Before adopting any free hosted tier, check current quota, inactivity behavior, data region, security controls, terms, and exit/export path. Record the decision here.
4. Do not put customer or other private documents into free notebooks, model APIs, or hosted databases unless the user has approved that data flow and the service is suitable for it.
5. Free services do not relax requirements for tenant isolation, encryption, backups, restore testing, or reproducible evaluation.

## Phase map

| Phase | Weeks | Purpose | Exit gate |
|---|---:|---|---|
| 0 — Discovery | 1–2 | Validate the market, use cases, evaluation data, and decisions before committing to the build. | J0: three pilot letters of intent. This project waived the gate to proceed; its evidence is still outstanding. |
| 1 — Technical foundation | 3–10 | Ingest, index, and retrieve tenant-isolated documents. No answer-generating LLM yet. | J1: recall@10 ≥ 80%, search p95 < 300 ms on one million passages, and no cross-tenant access in tests. |
| 2 — Generation and trust | 11–18 | Generate streamed, cited answers with factual-consistency scores; make the product demonstrable. | J2: demo shown to three prospects; recall@10 ≥ 85%, hallucination rate < 5%, first token p95 < 3 s. |
| 3 — Go-to-market | 19–22 | Let a new customer onboard, connect a source, use the product, and receive a correct usage bill. | J3: an external tester completes setup and gets a cited answer within one day without help; test invoice is correct. |
| 4 — Pilots and launch | 23–26 | Run paid pilots, close security and quality gaps, then launch. Freeze feature work. | J4: three paying customers, all 19 Must requirements accepted, no open critical vulnerability, and final quality checks pass. |

## Phase 0 — Discovery (weeks 1–2)

**Purpose:** confirm that the product solves a real customer problem and establish the evidence and decisions the engineering work needs.

### Work

**Week 1**
- Choose a pilot sector and country; record why that market is a suitable first target.
- Build a list of 30 prospects, contact 15, and schedule 10 interviews.
- Prepare an interview guide covering source documents, frequent questions, hosting/data-residency needs, security constraints, and budget.
- Confirm availability for the six planned roles: CTO, ML engineer, two backend engineers, frontend engineer, and DevOps engineer.

**Week 2**
- Complete 10 interviews and rank three use cases by value, feasibility, and access to evaluation material.
- Assemble an evaluation set with at least 500 permitted real or public documents and 200 questions with reference answers. Keep private customer content and derived data out of Git.
- Record the chosen technical stack, hosting provider, and region—or explicitly record each as undecided.
- Map requirements EF-01 through EF-26 to a prioritized backlog.
- Check commercial-use licenses for HHEM-2.1-Open, BGE-M3, the reranker, and the selected open LLM.

### Deliverables and gate

- Interview synthesis and prioritized use cases.
- Evaluation corpus and reference questions, with data provenance and handling documented.
- Prioritized requirements backlog and stack/hosting decision record.
- **J0:** at least three pilot letters of intent. If fewer than three, the source roadmap says to revisit the sector or country before proceeding. In this project, J0 was waived by explicit decision; record any later evidence separately.

## Phase 1 — Technical foundation (weeks 3–10)

**Purpose:** send a document through the API, extract and index its content, then retrieve relevant passages without exposing another tenant's data. Do not add answer generation in this phase.

### Sprint 1 — Infrastructure and accounts (weeks 3–4) — Active

- Define staging and production Kubernetes environments in Terraform, plus a CI/CD build, test, and deployment pipeline. **Blocked on the hosting provider and region decision.**
- Run PostgreSQL, S3-compatible storage, and the queue/cache service with a documented backup and restore procedure.
- Configure Keycloak organizations, users, and Admin / Developer / Reader roles (EF-01).
- Complete the FastAPI/OpenAPI foundation, scoped API keys, and per-key rate limits.

**Sprint evidence:** repeatable local development; verified container build and health; staging/production deployment target documented; backup restore demonstrated; role and API-key permissions tested. Do not call the sprint complete based only on the current API skeleton.

#### Local on-demand backup procedure

- Start the complete local stack and create an archive with `uv run python scripts/local_backup.py backup --env-file .env`.
- The utility cleanly stops PostgreSQL, Valkey, SeaweedFS, and Qdrant, archives their named Docker volumes, then restarts the services. It writes a timestamped backup and manifest under `.backups/`, which is gitignored.
- Restore with `uv run python scripts/local_backup.py restore --env-file .env --manifest .backups/<timestamp>/manifest.json`. Restore checks the Compose project and volume names, then requires typing `RESTORE` before replacing volume contents. `--yes` is an explicit confirmation for non-interactive use.
- Restore only into the same Compose project with compatible service versions. If a restore fails partway through, services remain stopped so partial data is not served.
- These archives are unencrypted and intended only for local development data. Copy them to an external drive manually if needed; do not treat this as production backup protection.

### Sprint 2 — Ingestion (weeks 5–6)

- Implement corpus create/list/delete and filterable metadata schema (EF-03).
- Accept files up to 100 MB through API or console, store them in S3, enqueue Celery processing, and expose queued/processed/failed status (EF-04).
- Extract text, headings, and tables; OCR scanned documents with Docling/OCR tooling (EF-05).
- Split extracted content into configurable passages with size and overlap settings (EF-05).

**Sprint evidence:** API integration tests cover supported formats, size limits, success/failure status, retries, and malformed or empty files. Prove tenant ownership is carried through upload, job, and object-storage paths.

### Sprint 3 — Indexing (weeks 7–8)

- Serve BGE-M3 embeddings through Text Embeddings Inference.
- Configure Qdrant dense and sparse indexes; choose a tenant-safe collection/namespace strategy.
- Index raw text and metadata; support document update and deletion (EF-06).
- Add automated isolation tests using at least two tenants.

**Sprint evidence:** indexed passages can be updated and deleted; repeat/retry behavior is safe; every read and write is scoped to the tenant; two-tenant tests demonstrate that neither tenant can access the other's content.

### Sprint 4 — Search (weeks 9–10)

- Add `POST /v1/query` in search-only mode: return passages, not generated answers.
- Implement hybrid dense + lexical search, configurable lexical weight, metadata filters, and pagination (EF-09).
- Add multilingual bge-reranker-v2-m3 and optional MMR diversity (EF-10).
- Run recall@10 evaluation automatically in CI against the Phase 0 dataset.

**J1 acceptance:** recall@10 ≥ 80%; search p95 < 300 ms at one million passages; zero cross-tenant access in automated tests. Keep the final MVP target of 85% visible; J1's 80% is an intermediate gate, not the final target.

## Phase 2 — Generation and trust (weeks 11–18)

**Purpose:** turn retrieved passages into a useful answer without losing grounding, citations, language support, or traceability.

### Sprint 5 — Grounded generation (weeks 11–12)

- Route every model call through LiteLLM; support a hosted open model and customer-supplied provider keys (EF-14).
- Require numbered citations pointing to the source document and passage (EF-11).
- Stream responses with Server-Sent Events (EF-13).
- Test French, English, and Arabic, including mixed-language retrieval.

### Sprint 6 — Chat and factual consistency (weeks 13–14)

- Store conversations and turns; use conversation history for follow-up questions (EF-12).
- Return a factual-consistency score from 0 to 1 with each answer and expose the standalone evaluation endpoint (EF-15).
- Return “I don't know” when no relevant evidence exists or the score is below the configured threshold.

**Scope note:** correction of unsupported claims (EF-16) and broader policy/PII guardrails (EF-17) are marked Should/V2 in the specification; do not silently expand this MVP sprint to include them.

### Sprint 7 — Web console (weeks 15–16)

- Build the Next.js console for authentication, corpus management, and uploads.
- Add a playground showing the question, retrieved passages, scores, citations, selected model, and cost (EF-21).
- Add member and scoped API-key management.

### Sprint 8 — Observability and quality (weeks 17–18)

- Trace each request end to end with OpenTelemetry and Langfuse (EF-24).
- Show storage, query volume, latency, and hallucination-rate metrics to the customer (EF-22).
- Tune chunking, hybrid weights, and reranking using the evaluation set; measure progress toward recall@10 ≥ 85%.
- Run initial load tests.

**J2 acceptance:** demonstrate the product to three prospects; recall@10 ≥ 85%; hallucination rate < 5%; first token p95 < 3 seconds. Answers must include citations and scores; do not use model-only knowledge as a fallback.

## Phase 3 — Go-to-market (weeks 19–22)

**Purpose:** make the MVP usable without an engineer guiding every step, and measure/bill usage accurately.

### Sprint 9 — Connectors and widget (weeks 19–20)

- Add scheduled and incremental web, Google Drive, and SharePoint synchronization (EF-07).
- Show connector credentials/status and report partial or failed syncs explicitly.
- Build an embeddable chat/search widget (EF-23).

### Sprint 10 — Billing and operations (weeks 21–22)

- Implement the 30-day quota-limited trial without a credit card (EF-02).
- Meter tenant storage and requests, enforce quotas, and produce usage invoices (EF-26).
- Publish API onboarding documentation and a status page.

**J3 acceptance:** an external tester can sign up, connect a source, and get a cited answer within one day without assistance; a test invoice matches measured usage.

## Phase 4 — Pilots and launch (weeks 23–26)

**Purpose:** validate the product with customers, remove critical risks, and launch. Freeze new feature development; focus on reliability, security, quality, and sales.

### Week 23 — Pilot onboarding
- Onboard three pilot customers; configure tenants, ingest their permitted documents, and build a customer-specific evaluation set.
- Agree measurable success criteria with each customer.

### Week 24 — Security and load
- Commission an external penetration test, emphasizing tenant isolation.
- Test 50 concurrent requests; fix bottlenecks and rerun the measurements.

### Week 25 — Pilot outcomes
- Resolve customer feedback on answer quality and usability.
- Convert pilots to paid contracts.

### Week 26 — Acceptance and launch
- Run the final acceptance checklist and document evidence for every Must requirement.
- Launch publicly and publish the demo and product information.
- Record lessons and create a separately scoped V2 backlog.

**J4 acceptance checklist**
- All 19 Must requirements pass their acceptance tests.
- Recall@10 ≥ 85%; hallucination rate < 5% on the pilot evaluation set.
- p95 latency targets hold under 50 concurrent requests.
- Penetration testing finds no cross-tenant access and no unresolved critical vulnerability.
- Public API documentation enables a basic integration in under 15 minutes.
- Usage billing has been reconciled over one pilot month.
- Three customers are paying.

## Requirement map

The EF identifiers below refer to the functional-requirement table in the source specification. “Must” items belong to MVP acceptance; Should/Could items marked V2/V3 are not silently pulled into the MVP.

| Work area | Requirements | Planned phase |
|---|---|---|
| Organizations, roles, trial | EF-01, EF-02 | Phase 1 Sprint 1; Phase 3 Sprint 10 |
| Corpus, upload, parsing, indexing | EF-03–EF-06 | Phase 1 Sprints 2–3 |
| Connectors and inherited source ACLs | EF-07; EF-08 is V2 | Phase 3 Sprint 9; inherited ACLs deferred |
| Hybrid retrieval and reranking | EF-09–EF-10 | Phase 1 Sprint 4 |
| Grounded generation, chat, streaming, model selection | EF-11–EF-14 | Phase 2 Sprints 5–6 |
| Factual-consistency score | EF-15 | Phase 2 Sprint 6 |
| Claim correction and broader guardrails | EF-16–EF-17, Should/V2 | Deferred |
| Agents and MCP | EF-18 (agent definition), EF-19 (MCP exposure), EF-20 (multi-agent/A2A) | V2/V3; deferred |
| Playground and customer dashboard | EF-21–EF-22 | Phase 2 Sprints 7–8 |
| Embeddable widget | EF-23 | Phase 3 Sprint 9 |
| Request tracing | EF-24 | Phase 2 Sprint 8 |
| Importing/evaluating customer Q&A sets | EF-25, Should/V2 | Deferred as a product feature |
| Usage metering and billing | EF-26 | Phase 3 Sprint 10 |

**Evaluation-set distinction:** the Phase 0 set of 200 reference questions is an internal engineering/evaluation asset used to measure retrieval and answer quality. EF-25 is a separate customer-facing feature for importing and evaluating datasets; it is marked Should/V2.

## Quality and security targets

- Retrieval: recall@10 ≥ 85% for final MVP acceptance; the earlier J1 gate is ≥ 80%.
- Search p95 < 300 ms; first generated token p95 < 3 s.
- Hallucination rate < 5%; each generated answer is cited and scored.
- SaaS availability target: 99.9% monthly. This is a release/operations target, not demonstrated by the current local stack.
- Ingestion target: at least 10,000 pages/hour/tenant.
- French, English, and Arabic support from MVP.
- Tenant isolation across API, jobs, object paths, databases, indexes, caches, and logs; no customer content used to train models.
- TLS 1.2+ in transit and AES-256 at rest for deployed customer environments; validate these controls in the actual deployment target.
- Run the evaluation suite on every release and maintain at least 70% automated test coverage.

## Explicitly outside MVP

Do not implement these unless the product scope is explicitly changed: inherited source permissions (EF-08), claim correction and advanced policy guardrails (EF-16–17), agents/MCP/A2A (EF-18–20), customer-managed evaluation import (EF-25), and the broader V2/V3 scope such as SSO, SDKs, VPC/Helm, on-premises/air-gapped deployments, multimodal ingestion, or agent workflows.

## Source documents

- `Roadmap MVP — Plateforme RAG.docx`: phase timing, weekly/sprint tasks, deliverables, and J0–J4 gates.
- `Vectara — Analyse & cahier des charges.docx`: product scope, EF-01–EF-26, architecture, technical choices, NFRs, risks, and final acceptance criteria.

If these sources conflict, preserve the stricter security rule, flag the discrepancy, and ask for a product decision rather than silently changing scope or thresholds.
