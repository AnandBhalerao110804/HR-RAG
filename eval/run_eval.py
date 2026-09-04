"""Evaluation harness: Precision@1, Recall@1, Precision@4, Recall@4, MRR,
and NDCG@4 for policy retrieval, and latency (TTFT, p50/p95/p99) for full
agent turns.

Usage: python -m eval.run_eval

Retrieval metrics hit only the local Chroma/BM25/reranker pipeline (no API
calls). Latency metrics run the golden set live through the real agent
(agent.run_turn_stream) -- this costs real API calls and takes a while.

Percentiles are computed via nearest-rank on the sorted sample. With this
golden set's size (~18 queries), p95/p99 end up close to the max -- a
small-sample estimate, not a statistically strong one. Good for tracking
relative change run over run, not for precise SLA claims.
"""

import json
import math
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from eval.golden_set import GOLDEN_SET
from hr_rag import agent
from hr_rag.sources import vector_store

K = 4
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _percentile(sorted_data: list[float], pct: float) -> float:
    if not sorted_data:
        return float("nan")
    idx = max(0, math.ceil(pct / 100 * len(sorted_data)) - 1)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def _dcg_at_k(ranked_relevance: list[int], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(ranked_relevance[:k]))


def evaluate_retrieval(k: int = K) -> list[dict]:
    rows = []
    for item in GOLDEN_SET:
        chunks = vector_store.search(item["query"], n_results=k)
        ranked_ids = [c.metadata["chunk_id"] for c in chunks]  # order preserved -- post-rerank ranking
        expected_ids = set(item["expected_chunk_ids"])
        retrieved_set = set(ranked_ids)
        hits_at_k = retrieved_set & expected_ids

        top1_relevant = int(bool(ranked_ids) and ranked_ids[0] in expected_ids)

        # Reciprocal rank of the first relevant hit within the top-k list (0 if none).
        reciprocal_rank = 0.0
        for i, cid in enumerate(ranked_ids, start=1):
            if cid in expected_ids:
                reciprocal_rank = 1.0 / i
                break

        # NDCG@k, binary relevance. IDCG assumes all relevant docs (up to k of
        # them) are ranked first -- true here since every golden item has 1-2
        # expected chunks, well under k=4.
        ranked_relevance = [1 if cid in expected_ids else 0 for cid in ranked_ids]
        dcg = _dcg_at_k(ranked_relevance, k)
        ideal_relevance = [1] * min(len(expected_ids), k)
        idcg = _dcg_at_k(ideal_relevance, k)
        ndcg = dcg / idcg if idcg > 0 else 0.0

        rows.append(
            {
                "query": item["query"],
                "expected": sorted(expected_ids),
                "retrieved": ranked_ids,
                "precision_at_1": top1_relevant / 1,
                "recall_at_1": top1_relevant / len(expected_ids),
                "precision_at_4": len(hits_at_k) / k,
                "recall_at_4": len(hits_at_k) / len(expected_ids),
                "reciprocal_rank": reciprocal_rank,
                "ndcg_at_4": ndcg,
            }
        )
    return rows


def evaluate_latency(employee_id: str = "E1001") -> list[dict]:
    rows = []
    for item in GOLDEN_SET:
        token = secrets.token_urlsafe(16)  # fresh thread per query -- cold-turn latency, no memory assist
        start = time.perf_counter()
        first_token_time = None
        for event in agent.run_turn_stream(token, employee_id, item["query"]):
            if event["type"] == "token" and first_token_time is None:
                first_token_time = time.perf_counter()
        end = time.perf_counter()
        rows.append(
            {
                "query": item["query"],
                "ttft_s": (first_token_time - start) if first_token_time else None,
                "total_latency_s": end - start,
            }
        )
    return rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _summarize(rows: list[dict]) -> dict:
    return {
        "mean_precision_at_1": _mean([r["precision_at_1"] for r in rows]),
        "mean_recall_at_1": _mean([r["recall_at_1"] for r in rows]),
        "mean_precision_at_4": _mean([r["precision_at_4"] for r in rows]),
        "mean_recall_at_4": _mean([r["recall_at_4"] for r in rows]),
        "mrr": _mean([r["reciprocal_rank"] for r in rows]),
        "mean_ndcg_at_4": _mean([r["ndcg_at_4"] for r in rows]),
        "k": K,
        "n_queries": len(rows),
    }


def _summarize_latency(rows: list[dict]) -> dict:
    ttfts = sorted(r["ttft_s"] for r in rows if r["ttft_s"] is not None)
    totals = sorted(r["total_latency_s"] for r in rows)
    missing_ttft = sum(1 for r in rows if r["ttft_s"] is None)
    return {
        "ttft_p50_s": _percentile(ttfts, 50),
        "ttft_p95_s": _percentile(ttfts, 95),
        "ttft_p99_s": _percentile(ttfts, 99),
        "total_p50_s": _percentile(totals, 50),
        "total_p95_s": _percentile(totals, 95),
        "total_p99_s": _percentile(totals, 99),
        "n_queries": len(rows),
        "n_missing_ttft": missing_ttft,
    }


def main():
    print(f"Running retrieval eval (k={K}) over {len(GOLDEN_SET)} golden queries...")
    retrieval_rows = evaluate_retrieval()
    retrieval_summary = _summarize(retrieval_rows)

    print(f"Running latency eval (live agent calls) over {len(GOLDEN_SET)} golden queries...")
    latency_rows = evaluate_latency()
    latency_summary = _summarize_latency(latency_rows)

    print()
    print("=== Retrieval ===")
    print(f"  k = {K}, n = {retrieval_summary['n_queries']}")
    print(f"  Precision@1: {retrieval_summary['mean_precision_at_1']:.3f}")
    print(f"  Recall@1:    {retrieval_summary['mean_recall_at_1']:.3f}")
    print(f"  Precision@{K}: {retrieval_summary['mean_precision_at_4']:.3f}")
    print(f"  Recall@{K}:    {retrieval_summary['mean_recall_at_4']:.3f}")
    print(f"  MRR:         {retrieval_summary['mrr']:.3f}")
    print(f"  NDCG@{K}:      {retrieval_summary['mean_ndcg_at_4']:.3f}")
    misses = [r for r in retrieval_rows if r["recall_at_4"] == 0]
    if misses:
        print(f"  Complete misses ({len(misses)}):")
        for r in misses:
            print(f"    - {r['query']!r} -> expected {r['expected']}, got {r['retrieved']}")

    print()
    print("=== Latency (n={}, small-sample estimate) ===".format(latency_summary["n_queries"]))
    print(f"  TTFT   p50={latency_summary['ttft_p50_s']:.2f}s  p95={latency_summary['ttft_p95_s']:.2f}s  p99={latency_summary['ttft_p99_s']:.2f}s")
    print(f"  Total  p50={latency_summary['total_p50_s']:.2f}s  p95={latency_summary['total_p95_s']:.2f}s  p99={latency_summary['total_p99_s']:.2f}s")
    if latency_summary["n_missing_ttft"]:
        print(f"  ({latency_summary['n_missing_ttft']} queries produced no text token at all -- excluded from TTFT)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = RESULTS_DIR / f"eval_{timestamp}.json"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retrieval": {"summary": retrieval_summary, "rows": retrieval_rows},
        "latency": {"summary": latency_summary, "rows": latency_rows},
    }
    report_path.write_text(json.dumps(report, indent=2))
    print()
    print(f"Full report written to {report_path}")


if __name__ == "__main__":
    main()
