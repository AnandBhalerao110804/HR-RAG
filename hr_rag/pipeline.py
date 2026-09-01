"""Orchestrates the request flow per PRD 5.5:
1. Authenticated query in
2. Source routing
3. Parallel retrieval
4. Light model attempt
5/6. Escalate to deep model if needed
7. Return answer with source attribution
"""

import time
from concurrent.futures import ThreadPoolExecutor

import anthropic

from hr_rag.guardrails import (
    ASSISTANT_UNAVAILABLE_ANSWER,
    NO_HR_INTENT_ANSWER,
    NO_SOURCE_ANSWER,
    has_relevant_content,
)
from hr_rag.logging_util import log_error, log_query
from hr_rag.models import PipelineResult, RetrievedChunk
from hr_rag.routing import model_router, source_router
from hr_rag.routing.source_router import NONE_SOURCE
from hr_rag.sources import employee_db, vector_store, web_search as web_search_source

_RETRIEVERS = {
    "policy_db": lambda employee_id, query: vector_store.search(query),
    "employee_db": lambda employee_id, query: employee_db.search(employee_id, query),
    "web_search": lambda employee_id, query: web_search_source.search(query),
}


def _retrieve_parallel(sources: list[str], employee_id: str, query: str) -> list[RetrievedChunk]:
    with ThreadPoolExecutor(max_workers=max(len(sources), 1)) as pool:
        futures = [pool.submit(_RETRIEVERS[s], employee_id, query) for s in sources]
        results = [f.result() for f in futures]
    return [chunk for chunks in results for chunk in chunks]


def run(employee_id: str, query: str) -> PipelineResult:
    try:
        return _run(employee_id, query)
    except anthropic.APIError as e:
        # Covers rate limits, transient 5xxs, and network errors from any of
        # the three API calls this pipeline can make (source classification,
        # light model, deep model) -- a quota/outage/blip shouldn't crash the
        # whole session, it should degrade to a clear "try again" message.
        log_error(employee_id=employee_id, query=query, error=e)
        return PipelineResult(
            query=query,
            answer=ASSISTANT_UNAVAILABLE_ANSWER,
            sources_selected=[],
            escalated=False,
            escalation_reason=None,
            cited_sources=[],
        )


def _run(employee_id: str, query: str) -> PipelineResult:
    start = time.monotonic()

    route_decision = source_router.route(query)

    if route_decision.sources == [NONE_SOURCE]:
        latency_ms = (time.monotonic() - start) * 1000
        log_query(
            employee_id=employee_id,
            query=query,
            sources_selected=route_decision.sources,
            escalated=False,
            escalation_reason=None,
            latency_ms=latency_ms,
        )
        return PipelineResult(
            query=query,
            answer=NO_HR_INTENT_ANSWER,
            sources_selected=route_decision.sources,
            escalated=False,
            escalation_reason=None,
            cited_sources=[],
        )

    chunks = _retrieve_parallel(route_decision.sources, employee_id, query)

    if not has_relevant_content(chunks):
        latency_ms = (time.monotonic() - start) * 1000
        log_query(
            employee_id=employee_id,
            query=query,
            sources_selected=route_decision.sources,
            escalated=False,
            escalation_reason=None,
            latency_ms=latency_ms,
        )
        return PipelineResult(
            query=query,
            answer=NO_SOURCE_ANSWER,
            sources_selected=route_decision.sources,
            escalated=False,
            escalation_reason=None,
            cited_sources=[],
        )

    model_answer = model_router.answer(query, chunks)
    escalated = model_answer.model_used == model_router.DEEP_MODEL

    latency_ms = (time.monotonic() - start) * 1000
    log_query(
        employee_id=employee_id,
        query=query,
        sources_selected=route_decision.sources,
        escalated=escalated,
        escalation_reason=model_answer.escalation_reason,
        latency_ms=latency_ms,
    )

    return PipelineResult(
        query=query,
        answer=model_answer.answer or NO_SOURCE_ANSWER,
        sources_selected=route_decision.sources,
        escalated=escalated,
        escalation_reason=model_answer.escalation_reason,
        cited_sources=model_answer.cited_sources,
    )
