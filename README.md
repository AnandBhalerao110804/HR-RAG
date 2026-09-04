# HR Portal RAG — v2

Implements `HR_RAG_Portal_PRD.md`'s three data sources (policy vector DB,
scoped employee SQLite, allowlisted web search) and two-tier adaptive model
routing (Claude Haiku 4.5 light model, escalating to Claude Sonnet 5) —
now as a **LangGraph tool-use agent** with **multi-turn memory** behind a
**web login + chat UI**, rather than v1's fixed one-shot pipeline. See
`Architecture` below for what changed and why.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY
```

## Initialize data

```bash
python data/seed_employees.py           # creates data/employees.db, prints the demo login password
python -m hr_rag.ingest data/policies/   # indexes policy docs into data/chroma_store/
```

Re-run the ingest command any time a policy doc under `data/policies/`
changes — indexing is a manual trigger, not automatic.

## Run

```bash
pytest tests/               # offline tests: auth, sessions, employee-record scoping, agent tool scoping
uvicorn api:app --reload    # web app -- open http://127.0.0.1:8000, log in as e.g. E1001
python cli.py                # terminal dev harness, same agent, no real login (skips straight to picking an employee id)
```

Log in with any sample employee id (`E1001`–`E1004`) and the demo password
printed by `seed_employees.py`. In one continuous chat session, try:
- "What's my PTO balance?" → answers directly, no escalation.
- A follow-up like "what about sick leave?" → answered from the *same*
  session's memory, without re-querying your record — confirms multi-turn
  memory is working.
- "Given my tenure, am I eligible for extended parental leave?" → the model
  calls both `search_employee_record` and `search_policy_db` itself and
  decides on its own whether it's confident enough to answer directly or
  needs to escalate.
- Something with no matching source (e.g. an out-of-scope policy) → declines
  rather than fabricating.

Each turn prints a structured JSON log line (query, tools used, escalation
status/reason, latency) — see `hr_rag/logging_util.py`.

## Architecture (v2)

The model is a real agent now, not a fixed pipeline: it calls
`search_policy_db`, `search_employee_record`, and `search_web` itself, as
many times as it decides it needs, and calls `escalate_to_deep_reasoning`
whenever *it* judges a question needs deeper reasoning — not a fixed rule
applied uniformly to every cross-source question. Built with **LangGraph**
(`hr_rag/agent.py`): a 3-node graph (`agent` → `tools` → `check_escalation`
→ loop back to `agent`), with conversation memory owned by LangGraph's
`MemorySaver` checkpointer, keyed by the session token as `thread_id`.

Auth (`hr_rag/auth.py`) is demo-grade: employee_id + a password checked
against a salted `pbkdf2_hmac` hash in the `employees` table — enough to
gate access and identify who's logged in, not enterprise security.

**Security invariant carried over from v1, now load-bearing**:
`search_employee_record`'s tool schema has no `employee_id` parameter —
its value is injected from graph state (`InjectedState`), never something
the model can see or set. A prompt-injected instruction inside a retrieved
document or web result cannot make the model exfiltrate another employee's
record, because there is no parameter through which to even attempt it
(`tests/test_agent_scoping.py` verifies this).

**Deliberate deviation from PRD FR6** ("deep model reuses context,
retrieval is never re-run"): the deep-tier model still has all tools bound
and *can* call one again if it identifies a genuine gap, since it's
continuing the same graph/state rather than receiving a fixed context
dump. In practice it doesn't redundantly redo a search it can already see
succeeded — but this is no longer structurally forbidden, just naturally
rare.

**Source conflict precedence** (unchanged from v1): `policy_db` >
`employee_db` > `web_search`. Defined in
`hr_rag.guardrails.SOURCE_PRIORITY` / `SOURCE_PRIORITY_INSTRUCTION`, folded
into the agent's system prompt and used to order chunks within
`wrap_untrusted()` before the model sees them.

## Notes / deferred

- Single-role access only; the RBAC extension point is documented in
  `hr_rag/sources/employee_db.py`.
- Conversation memory is in-memory only (LangGraph `MemorySaver`) — lost on
  process restart, and `/logout` doesn't clear the underlying checkpoint
  (a new login gets a new token/thread anyway, so this is harmless, just
  worth knowing).
- Guardrails remain the v1 minimum (PII regex redaction in logs,
  untrusted-context wrapping, source-priority resolution) — detailed
  guardrail design is still an explicit follow-up, not solved here.
