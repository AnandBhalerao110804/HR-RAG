# HR Portal RAG — v1 Prototype

Local prototype implementing `HR_RAG_Portal_PRD.md`: three data sources
(policy vector DB, scoped employee SQLite, allowlisted web search) and
two-tier adaptive model routing (Claude Haiku 4.5 light model, escalating
to Claude Sonnet 5 on ambiguity/low confidence).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY
```

## Initialize data

```bash
python data/seed_employees.py           # creates data/employees.db
python -m hr_rag.ingest data/policies/   # indexes policy docs into data/chroma_store/
```

Re-run the ingest command any time a policy doc under `data/policies/`
changes — indexing is a manual trigger in v1 (see PRD open questions).

## Run

```bash
pytest tests/         # offline tests: routing heuristics, record scoping, no-fabrication
python cli.py          # interactive REPL, pick a sample employee id to "log in"
```

Try asking:
- "What's my PTO balance?" — resolves via the light model, `employee_db` only.
- "Am I eligible for the sabbatical program given my tenure?" — cross-source, escalates to the deep model.
- "I want to expense $600, do I need extra approval?" — cross-source (expense policy tiers + your submitted expenses).
- "What's my pay band?" — hits the `compensation` table, still scoped to the logged-in employee only.
- "What's the current minimum wage in California?" — routed to allowlisted web search.
- Something out of scope — the system should decline rather than fabricate.

Each query prints a structured JSON log line (query, sources selected,
escalation status/reason, latency) — see `hr_rag/logging_util.py`.

## Design decisions

- **Source conflict precedence**: when retrieved sources disagree, the model
  resolves it as `policy_db` (company policy) > `employee_db` (the
  employee's own record) > `web_search` (external, least authoritative).
  Defined in `hr_rag.guardrails.SOURCE_PRIORITY` / `SOURCE_PRIORITY_INSTRUCTION`,
  enforced two ways: `wrap_untrusted()` orders retrieved chunks by this
  priority before they're shown to the model, and both the light and deep
  model system prompts (`hr_rag/routing/model_router.py`) are given the rule
  explicitly and told to say so when they had to apply it. Conflicts the
  precedence rule doesn't cleanly resolve (e.g. two policy_db chunks
  disagreeing with each other) still trigger escalation to the deep model.

## Notes / deferred (see PRD section 8)

- Single-role access only; the RBAC extension point is documented in
  `hr_rag/sources/employee_db.py`.
- Guardrails are the v1 minimum only (PII regex redaction in logs,
  untrusted-context wrapping, confidence-threshold escalation) — detailed
  guardrail design is an explicit follow-up, not solved here.
