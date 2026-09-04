from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    source: str  # "policy_db" | "employee_db" | "web_search"
    text: str
    metadata: dict = field(default_factory=dict)
