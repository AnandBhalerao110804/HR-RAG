"""In-memory auth-session map: token -> employee_id.

This does NOT hold conversation state -- that lives in LangGraph's
MemorySaver checkpointer, keyed by the same token used as the LangGraph
thread_id (see hr_rag/agent.py). This module only answers "who is this
token logged in as," matching the "in-memory per session, resets on
restart" decision.
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

_SESSIONS: dict[str, "AuthSession"] = {}


@dataclass
class AuthSession:
    employee_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def create_session(employee_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = AuthSession(employee_id=employee_id)
    return token


def get_session(token: str) -> AuthSession | None:
    return _SESSIONS.get(token)


def delete_session(token: str) -> None:
    _SESSIONS.pop(token, None)
