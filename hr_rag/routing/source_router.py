"""Source routing (PRD 5.2): decide which data source(s) a query needs,
resolved upfront before generation.
"""

import json
import re

import anthropic

from hr_rag.config import ANTHROPIC_API_KEY, LIGHT_MODEL
from hr_rag.models import SourceRouteDecision

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SELF_REFERENCE_RE = re.compile(r"\b(my|i|i've|i'm|me)\b", re.IGNORECASE)
_EMPLOYEE_DOMAIN_RE = re.compile(
    r"\b(balances?|leaves?|pto|sick|tenure|hire date|start date|departments?|"
    r"records?|salar\w*|pay ?bands?|compensation|comp\b|raises?|expenses?|"
    r"reimburse\w*|managers?|status|requests?|approv\w*|pending|schedules?|"
    r"days? ?off|time ?off)\b",
    re.IGNORECASE,
)
_POLICY_PATTERNS = re.compile(
    r"\b(policy|eligible|eligibility|entitled|allowed|how many days|program)\b",
    re.IGNORECASE,
)
_WEB_PATTERNS = re.compile(
    r"\b(current law|minimum wage|tax bracket|labor law|regulation|market rate|"
    r"benchmark|latest|this year's)\b",
    re.IGNORECASE,
)

# Whole-message greetings/chitchat with no HR intent -- matched against the
# full stripped query so it doesn't accidentally eat a real question that
# happens to start with "hi" or "thanks".
_GREETING_RE = re.compile(
    r"^(hi+|hello+|hey+|yo|sup|good morning|good afternoon|good evening|"
    r"thanks?( you)?|thank you( so much)?|bye|goodbye|see you|ok|okay|cool|"
    r"test|testing)[!.? ]*$",
    re.IGNORECASE,
)

# "none" means no data source applies -- pure chitchat or something outside
# HR scope entirely (e.g. "tell me a joke"). Kept distinct from the
# no-relevant-content guard in guardrails.py, which fires *after* a real
# retrieval comes back empty; this fires *before* any retrieval happens.
NONE_SOURCE = "none"
_ALL_SOURCES = ["policy_db", "employee_db", "web_search", NONE_SOURCE]

_CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": {"type": "string", "enum": _ALL_SOURCES},
            "minItems": 1,
        }
    },
    "required": ["sources"],
    "additionalProperties": False,
}


def _heuristic_route(query: str) -> list[str]:
    if _GREETING_RE.match(query.strip()):
        return [NONE_SOURCE]

    sources = []
    if _SELF_REFERENCE_RE.search(query) and _EMPLOYEE_DOMAIN_RE.search(query):
        sources.append("employee_db")
    if _POLICY_PATTERNS.search(query):
        sources.append("policy_db")
    if _WEB_PATTERNS.search(query):
        sources.append("web_search")
    return sources


def _classify_with_light_model(query: str) -> list[str]:
    response = _client.messages.create(
        model=LIGHT_MODEL,
        max_tokens=256,
        system=(
            "You are a router for an HR portal. Decide which data sources are "
            "needed to answer the employee's question:\n"
            "- policy_db: company policy documents (leave, benefits, eligibility rules)\n"
            "- employee_db: the asking employee's own personal record (their balance, "
            "tenure, department, etc.)\n"
            "- web_search: external/regulatory info (current law, tax brackets, market data)\n"
            "- none: the message is chitchat, a greeting, or otherwise has no HR intent "
            "and doesn't need any data source\n"
            "Select every source that is actually needed; a question comparing a policy "
            "rule against the employee's own attributes needs both policy_db and "
            "employee_db. Use \"none\" alone (not combined with other sources) when "
            "nothing applies."
        ),
        output_config={"format": {"type": "json_schema", "schema": _CLASSIFY_SCHEMA}},
        messages=[{"role": "user", "content": query}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["sources"]


def route(query: str) -> SourceRouteDecision:
    heuristic_sources = _heuristic_route(query)
    if heuristic_sources:
        return SourceRouteDecision(sources=heuristic_sources, method="heuristic")

    classified = _classify_with_light_model(query)
    return SourceRouteDecision(sources=classified, method="light_model_classification")
