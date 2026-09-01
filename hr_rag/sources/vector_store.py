"""Chroma-backed policy document vector store, with hybrid retrieval.

Documents are chunked by policy section (split on markdown headings) and
tagged with metadata (department, region, effective_date) so retrieval can
be filtered, and so a stale chunk is at least visible via last_indexed
rather than silently trusted (PRD open question: policy re-indexing).

Search combines dense (Chroma/MiniLM embeddings) and sparse (BM25 keyword)
retrieval via Reciprocal Rank Fusion -- dense catches semantic/paraphrased
matches, BM25 catches exact terms (policy IDs, specific numbers, exact
phrasing) that embeddings can blur.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi

from hr_rag.config import CHROMA_DIR
from hr_rag.models import RetrievedChunk

COLLECTION_NAME = "policy_docs"

# Reciprocal Rank Fusion constant -- the standard default (Cormack et al.).
# Higher values flatten the weight given to top ranks; 60 is the usual choice
# and isn't sensitive to tuning at this corpus size.
_RRF_K = 60

# In-process cache of the BM25 index over the full collection, since BM25
# has no persistent store of its own (unlike Chroma). Invalidated whenever
# index_policy_docs() re-ingests, so it never serves a stale corpus.
_bm25_cache = None


def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(COLLECTION_NAME)


def _get_bm25():
    global _bm25_cache
    if _bm25_cache is None:
        collection = _get_collection()
        data = collection.get()
        ids, docs, metadatas = data["ids"], data["documents"], data["metadatas"]
        tokenized = [doc.lower().split() for doc in docs]
        bm25 = BM25Okapi(tokenized) if docs else None
        _bm25_cache = (bm25, ids, docs, metadatas)
    return _bm25_cache


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Very small YAML-frontmatter parser for `key: value` pairs only."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


def _chunk_by_heading(body: str) -> list[str]:
    sections = re.split(r"\n(?=## )", body)
    return [s.strip() for s in sections if s.strip()]


def index_policy_docs(policies_dir: Path) -> int:
    """Re-indexes every .md file in policies_dir into Chroma. Manual trigger
    only (v1 decision) -- run via `python -m hr_rag.ingest data/policies/`
    whenever policy docs change."""
    global _bm25_cache
    _bm25_cache = None  # invalidate -- corpus is about to change

    collection = _get_collection()

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids, docs, metadatas = [], [], []
    now = datetime.now(timezone.utc).isoformat()

    for path in sorted(Path(policies_dir).glob("*.md")):
        raw = path.read_text()
        meta, body = _parse_frontmatter(raw)
        chunks = _chunk_by_heading(body)
        for i, chunk in enumerate(chunks):
            ids.append(f"{path.stem}-{i}")
            docs.append(chunk)
            metadatas.append(
                {
                    "title": meta.get("title", path.stem),
                    "department": meta.get("department", "All"),
                    "region": meta.get("region", "Global"),
                    "effective_date": meta.get("effective_date", ""),
                    "last_indexed": now,
                    "source_file": path.name,
                }
            )

    if docs:
        collection.add(ids=ids, documents=docs, metadatas=metadatas)
    return len(docs)


def search(query: str, n_results: int = 4) -> list[RetrievedChunk]:
    """Hybrid retrieval: fuses dense (embedding) and sparse (BM25) rankings
    via Reciprocal Rank Fusion, so an exact-term match (a specific number,
    a policy ID, precise phrasing) can surface a chunk that's semantically
    distant, alongside paraphrase/semantic matches dense search is good at.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    fetch_k = min(max(n_results * 3, 10), collection.count())

    dense = collection.query(query_texts=[query], n_results=fetch_k)
    dense_ids = dense["ids"][0]

    bm25, all_ids, all_docs, all_metadatas = _get_bm25()
    bm25_ids = []
    if bm25 is not None:
        scores = bm25.get_scores(query.lower().split())
        ranked_indices = sorted(range(len(all_ids)), key=lambda i: scores[i], reverse=True)
        bm25_ids = [all_ids[i] for i in ranked_indices[:fetch_k]]

    rrf_scores: dict[str, float] = {}
    for rank, id_ in enumerate(dense_ids, start=1):
        rrf_scores[id_] = rrf_scores.get(id_, 0.0) + 1.0 / (_RRF_K + rank)
    for rank, id_ in enumerate(bm25_ids, start=1):
        rrf_scores[id_] = rrf_scores.get(id_, 0.0) + 1.0 / (_RRF_K + rank)

    top_ids = sorted(rrf_scores, key=lambda id_: rrf_scores[id_], reverse=True)[:n_results]

    id_to_doc = dict(zip(all_ids, all_docs))
    id_to_meta = dict(zip(all_ids, all_metadatas))

    return [
        RetrievedChunk(source="policy_db", text=id_to_doc[id_], metadata=id_to_meta[id_])
        for id_ in top_ids
    ]
