"""FastAPI web layer: login, chat, logout, and the static chat UI.

Auth is demo-grade (see hr_rag/auth.py) -- enough to gate access and
identify who's logged in for this prototype, not enterprise-grade.
"""

import anthropic
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel

from hr_rag import agent, auth, session_store
from hr_rag.guardrails import ASSISTANT_UNAVAILABLE_ANSWER
from hr_rag.logging_util import log_error, log_query
import time

app = FastAPI(title="HR Portal RAG")
app.mount("/static", StaticFiles(directory="static"), name="static")


class LoginRequest(BaseModel):
    employee_id: str
    password: str


class LoginResponse(BaseModel):
    token: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    escalated: bool
    escalation_reason: str | None
    tools_used: list[str]


def _require_session(authorization: str | None) -> tuple[str, session_store.AuthSession]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    session = session_store.get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return token, session


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if not auth.verify_login(body.employee_id, body.password):
        raise HTTPException(status_code=401, detail="Invalid employee id or password")
    token = session_store.create_session(body.employee_id)
    return LoginResponse(token=token)


@app.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token, _ = _require_session(authorization)
    session_store.delete_session(token)
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, authorization: str | None = Header(default=None)):
    token, session = _require_session(authorization)
    start = time.monotonic()
    try:
        result = agent.run_turn(token, session.employee_id, body.message)
    except (anthropic.AnthropicError, GraphRecursionError) as e:
        log_error(employee_id=session.employee_id, query=body.message, error=e)
        return ChatResponse(
            answer=ASSISTANT_UNAVAILABLE_ANSWER,
            escalated=False,
            escalation_reason=None,
            tools_used=[],
        )

    latency_ms = (time.monotonic() - start) * 1000
    log_query(
        employee_id=session.employee_id,
        query=body.message,
        sources_selected=result.tools_used,
        escalated=result.escalated,
        escalation_reason=result.escalation_reason,
        latency_ms=latency_ms,
    )
    return ChatResponse(
        answer=result.answer,
        escalated=result.escalated,
        escalation_reason=result.escalation_reason,
        tools_used=result.tools_used,
    )
