# HR Portal RAG System — Product Requirements Document

**Status:** Draft v0.1
**Last updated:** August 31, 2026

---

## 1. Overview

This document specifies requirements for a Retrieval-Augmented Generation (RAG) system powering an internal HR portal. Employees query the system in natural language to get answers grounded in company policy and their own employee records. The system draws from three data sources and uses two tiers of language models to balance response speed against reasoning quality.

## 2. Goals

- Give employees fast, self-service answers to HR questions without always requiring a human HR rep.
- Ground every answer in an actual retrieved source (policy doc, personal record, or web result) rather than model memory, since a confidently wrong HR answer carries real compliance risk.
- Use a lighter, cheaper model for simple lookups and reserve deeper reasoning for questions that actually need it, controlling cost without sacrificing quality on hard questions.

## 3. Scope

### In scope (v1)
- Three data sources: vector DB (policy docs), SQLite (employee records), web search
- Two-tier LLM setup: a light model and a deep model
- Source routing (which data source(s) a query needs) and adaptive model routing (light model attempts first, escalates when needed)
- Single-role access model (see Section 4)
- General guardrail principles (see Section 5.4); detailed implementation deferred

### Out of scope for v1 (candidates for later phases)
- Multi-role access (manager, HR-admin tiers)
- Human escalation workflow / hand-off to a live HR rep
- Multi-turn conversation memory
- Semantic caching of repeat queries
- Formal evaluation/feedback loop and logging dashboard
- Full citation UI / audit trail beyond basic source tagging

## 4. User & Access Model

v1 ships with a single role: **Employee (self-service)**.

- Every user is authenticated, and every query is automatically scoped to their own identity.
- Employee-record lookups can only ever return the authenticated user's own record — there is no cross-employee visibility and no separate manager or HR-admin tier in v1.
- This is a scope decision, not a security exemption: one role means everyone has the same self-service permissions, not that access control is skipped. The underlying record-scoping — a user can only query their own data — still applies at the data layer.
- Manager and HR-admin roles, with broader visibility into team or org-wide data, are deferred to a later phase.

## 5. System Architecture

### 5.1 Data sources

| Source | Content | Access pattern |
|---|---|---|
| Vector DB | Company policy documents | Semantic search, chunked by policy section, filterable by metadata (department, region, effective date) |
| SQLite | Employee records | Scoped queries only — parameterized functions (e.g. `get_my_leave_balance()`) or row-level security keyed to the authenticated user; never open text-to-SQL against the full table |
| Web search | External/regulatory info (labor law updates, tax brackets, market benchmarks) | Constrained to a trusted domain allowlist; results cached |

### 5.2 Routing layer

Two distinct routing decisions, resolved at different points in the pipeline:

**Source routing** (resolved upfront, before generation):
- Fast keyword/pattern heuristics handle the obvious cases (e.g. "my", "balance" → employee DB; "policy", "eligible" → policy KB; "current law", "minimum wage" → web search)
- Ambiguous queries fall back to a classification call using the light model
- Output: the set of sources to query, fetched in parallel

**Model routing** (resolved after retrieval, adaptively):
- The light model always sees the query plus retrieved context first
- It either answers directly, or calls an `escalate(reason)` function to hand off to the deep model
- The deep model receives the original query, the already-retrieved context, and the light model's stated escalation reason — retrieval is not re-run

Escalation triggers to encode in the light model's instructions: cross-source joins (e.g. matching a policy threshold against a specific employee attribute), ambiguous or conflicting retrieved content, comparative/hypothetical phrasing, low self-rated confidence.

### 5.3 Generation layer

- **Light model** — fast, low-cost; handles direct lookups and simple synthesis
- **Deep model** — invoked only on escalation; handles multi-source reasoning and policy interpretation

### 5.4 Guardrails (general description)

Guardrails will be refined iteratively as the system is built. At minimum, v1 should account for:
- Not answering confidently when no relevant source was retrieved
- Treating retrieved content (web results, policy docs) as untrusted input, not as instructions to follow
- Some form of source attribution in the answer, so a claim can be traced back to its origin
- Basic PII hygiene in logs and traces

Detailed guardrail design — PII redaction specifics, prompt-injection defenses, confidence thresholds — is deferred and tracked as a follow-up rather than specified here.

### 5.5 Request flow (reference)

1. Employee submits an authenticated query
2. Source router selects the relevant source(s): policy vector DB, employee SQLite, web search
3. Retrieval executes in parallel across selected sources
4. Light model attempts an answer using the retrieved context
5. If confident → answer is returned directly
6. If not confident → escalates to the deep model with its reason and the retrieved context → deep model answers
7. Final answer is returned with source attribution

## 6. Functional Requirements

- **FR1** — The system shall accept a natural-language query from an authenticated employee.
- **FR2** — The system shall determine which of the three data sources are relevant before retrieval begins.
- **FR3** — The system shall retrieve from all relevant sources in parallel.
- **FR4** — The system shall scope all employee-record retrieval to the authenticated user's own record.
- **FR5** — The light model shall attempt to answer using retrieved context, and shall escalate to the deep model when it cannot answer confidently.
- **FR6** — When escalating, the system shall pass the deep model the original query, retrieved context, and the light model's escalation reason, without re-running retrieval.
- **FR7** — The system shall return an answer grounded in retrieved content, with a general indication of source per claim.
- **FR8** — The system shall handle the case where no source returns relevant content without fabricating an answer.

## 7. Non-Functional Requirements

- **Security** — employee-record access must be scoped to the requester's identity at the data layer, not just via prompt-level instruction.
- **Latency** — the light-model path should resolve materially faster than the escalated path, since it's expected to serve the majority of queries.
- **Extensibility** — the routing layer and access model should be structured so that additional roles (manager, HR admin), additional data sources, or a human-escalation path can be added without a redesign.

## 8. Open Questions & Risks

- What's the actual mix of query types in practice? Needed to validate the source-router heuristics and estimate the escalation rate and cost.
- How will policy document updates get re-indexed into the vector DB, and how do we avoid serving stale policy text in the meantime?
- At what point does deferring multi-role RBAC become a real risk — e.g. once manager or HR-admin users need broader access?
- Guardrail specifics (PII handling, injection defenses, confidence thresholds) are explicitly unresolved and tracked as a follow-up, not a v1 blocker.

## 9. Success Metrics (draft — refine once usage data exists)

- % of queries resolved by the light model alone (cost/latency indicator)
- % of queries escalated to the deep model
- Answer accuracy / groundedness (e.g. via periodic manual review or user feedback)
- Repeat-query rate on the same topic (may indicate an unclear or wrong first answer)
