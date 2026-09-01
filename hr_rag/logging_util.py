"""Structured query logging.

Concrete implementation of PRD open question #1 ("what's the actual mix of
query types in practice?") -- every pipeline run emits one JSON line with
enough structure to later compute escalation rate and source-selection
mix, without building the full eval/logging dashboard (still out of scope
for v1).
"""

import json
import logging
from datetime import datetime, timezone

from hr_rag.guardrails import redact_pii

logger = logging.getLogger("hr_rag")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_query(
    *,
    employee_id: str,
    query: str,
    sources_selected: list[str],
    escalated: bool,
    escalation_reason: str | None,
    latency_ms: float,
) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "employee_id": employee_id,  # internal id, not PII by itself
        "query": redact_pii(query),
        "sources_selected": sources_selected,
        "escalated": escalated,
        "escalation_reason": escalation_reason,
        "latency_ms": round(latency_ms, 1),
    }
    logger.info(json.dumps(record))


def log_error(*, employee_id: str, query: str, error: Exception) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "employee_id": employee_id,
        "query": redact_pii(query),
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    logger.error(json.dumps(record))
