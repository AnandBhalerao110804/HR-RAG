from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    source: str  # "policy_db" | "employee_db" | "web_search"
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SourceRouteDecision:
    sources: list[str]
    method: str  # "heuristic" | "light_model_classification"


@dataclass
class ModelAnswer:
    action: str  # "answer" | "escalate"
    answer: str | None
    confidence: float
    cited_sources: list[str]
    escalation_reason: str | None
    model_used: str


@dataclass
class PipelineResult:
    query: str
    answer: str
    sources_selected: list[str]
    escalated: bool
    escalation_reason: str | None
    cited_sources: list[str]
