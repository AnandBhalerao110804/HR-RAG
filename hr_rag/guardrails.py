"""General guardrail primitives (PRD 5.4). Detailed guardrail design (PII
redaction specifics, prompt-injection defenses, confidence thresholds) is
explicitly deferred by the PRD -- this implements the stated v1 minimum:
untrusted-context wrapping, no-source fabrication guard, and log PII hygiene.
"""

import re

from hr_rag.models import RetrievedChunk

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SSN_LIKE_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")


def redact_pii(text: str) -> str:
    """Best-effort regex redaction for logs/traces -- not a substitute for a
    real PII classifier, but covers the common accidental-leak patterns."""
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _SSN_LIKE_RE.sub("[REDACTED_SSN]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


# Precedence when sources disagree: company policy is the authoritative
# rule, an employee's own record is fact about them specifically, and web
# results are the least authoritative (external, not vetted by HR). Ties
# should not occur in practice since each source answers a different kind
# of question, but the model still needs an explicit rule for phrasing
# like "the policy says X, but the search result said Y."
SOURCE_PRIORITY = {"policy_db": 0, "employee_db": 1, "web_search": 2}

SOURCE_PRIORITY_INSTRUCTION = (
    "If retrieved sources conflict, resolve the conflict using this precedence "
    "(highest first): company policy (policy_db) > the employee's own record "
    "(employee_db) > web search (web_search). Say so explicitly if you had to "
    "apply this precedence to resolve a conflict."
)


def wrap_untrusted(chunks: list[RetrievedChunk]) -> str:
    """Renders retrieved content as clearly-delimited untrusted data blocks,
    so the model treats it as data to reason over, not instructions to
    follow (PRD 5.4: treat retrieved content as untrusted input).

    Blocks are ordered by SOURCE_PRIORITY (policy_db first, then
    employee_db, then web_search) so the precedence is visible in the
    context itself, on top of the explicit instruction the caller should
    pair with this via SOURCE_PRIORITY_INSTRUCTION."""
    if not chunks:
        return "<untrusted_context>\n(no relevant content retrieved)\n</untrusted_context>"

    ordered = sorted(chunks, key=lambda c: SOURCE_PRIORITY.get(c.source, 99))
    blocks = []
    for chunk in ordered:
        blocks.append(
            f'<untrusted_context source="{chunk.source}">\n{chunk.text}\n</untrusted_context>'
        )
    return "\n".join(blocks)


def has_relevant_content(chunks: list[RetrievedChunk]) -> bool:
    return any(chunk.text.strip() for chunk in chunks)


ASSISTANT_UNAVAILABLE_ANSWER = (
    "Sorry, the assistant is temporarily unavailable (a backend request "
    "failed). Please try again in a moment, or reach out to HR directly if "
    "this keeps happening."
)

NO_HR_INTENT_ANSWER = (
    "Hi! I can help answer questions about company policy, your own HR "
    "records (leave, compensation, expenses, etc.), or general regulatory "
    "info. What would you like to know?"
)

NO_SOURCE_ANSWER = (
    "I couldn't find anything in your records, company policy, or approved "
    "web sources that answers this. Please rephrase your question or reach "
    "out to HR directly so a person can help."
)
