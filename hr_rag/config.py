import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

LIGHT_MODEL = "claude-haiku-4-5"
DEEP_MODEL = "claude-sonnet-5"

ROOT_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT_DIR / "data" / "chroma_store"
EMPLOYEE_DB_PATH = ROOT_DIR / "data" / "employees.db"

# v1-only: below this, the light model's answer was treated as low-confidence
# and escalated even without an explicit escalate call. Superseded in v2 by
# the model calling escalate_to_deep_reasoning itself; kept only in case v1's
# pipeline.py-era code paths are ever revisited.
CONFIDENCE_THRESHOLD = 0.7

# LangGraph's built-in loop cap (config.recursion_limit on graph.invoke) --
# guards against a runaway agent/tool-call loop within a single turn.
MAX_ITERATIONS = 12

PASSWORD_HASH_ITERATIONS = 100_000

# Web search is restricted to this allowlist (PRD 5.1: "Constrained to a
# trusted domain allowlist"). Extend as needed for real regulatory sources.
WEB_SEARCH_ALLOWED_DOMAINS = [
    "dol.gov",
    "irs.gov",
    "sec.gov",
    "eeoc.gov",
]
WEB_SEARCH_MAX_USES = 3

# Local cross-encoder reranker applied after hybrid (dense+BM25) fusion in
# vector_store.search(). Small, fast, well-established for this exact task.
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# How many RRF-fused candidates to hand to the reranker before cutting down
# to the final n_results -- wider than n_results so reranking has real
# candidates to re-order, not just re-confirm the fusion's top few.
RERANK_POOL_SIZE = 20
