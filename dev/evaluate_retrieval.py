from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from astrofairy import Workshop
from astrofairy._search import PROFILE, PROFILE_ID, SearchIndex

FIXTURE = Path(__file__).resolve().parent / "retrieval_eval/af-retrieval-v1.json"
MIB = 1024 * 1024


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _adopt(workshop: Workshop, asset: dict[str, Any], *, metadata_only: bool) -> str:
    proposal = {
        key: asset[key] for key in ("name", "scope", "kind", "summary", "tags", "content", "evidence")
    }
    if metadata_only:
        if asset["kind"] == "workflow":
            steps = asset["content"]["steps"]
            proposal["content"] = {
                "steps": [{"instruction": "placeholder body", "done": "placeholder done"} for _ in steps]
            }
        else:
            proposal["content"] = "placeholder body for body-benefit comparison"
    ref = workshop.library.propose(proposal)
    task = workshop.validation_task(ref)
    workshop.submit(task, {"op": "check"})
    workshop.submit(
        task,
        {
            "op": "review",
            "criterion": "asset-fitness",
            "verdict": "pass",
            "basis": "Frozen retrieval fixture adopted to exercise the real index; not a user-quality claim",
        },
    )
    workshop.submit(task, {"op": "close", "outcome": "complete"})
    workshop.library.adopt(ref, task, "stable")
    return ref


def _build(home: Path, corpus: dict[str, Any], *, metadata_only: bool, model_cache: Path) -> Workshop:
    workshop = Workshop(home)
    workshop.library.search_index = SearchIndex(workshop.store, model_cache=model_cache)
    for asset in corpus["assets"]:
        _adopt(workshop, asset, metadata_only=metadata_only)
    return workshop


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _where(scope: str | None, kind: str | None) -> str | None:
    clauses = []
    if scope is not None:
        clauses.append(f"scope = {_quote(scope)}")
    if kind is not None:
        clauses.append(f"kind = {_quote(kind)}")
    return " AND ".join(clauses) if clauses else None


def _rank(rows: list[dict[str, Any]]) -> list[str]:
    scores: dict[str, tuple[float, str]] = {}
    for row in rows:
        name = row.get("name")
        if not isinstance(name, str):
            continue
        if "_relevance_score" in row:
            score = float(row["_relevance_score"])
        elif "_score" in row:
            score = float(row["_score"])
        elif "_distance" in row:
            score = -float(row["_distance"])
        else:
            score = 0.0
        previous = scores.get(name)
        if previous is None or score > previous[0]:
            scores[name] = (score, name)
    return [name for score, name in sorted(scores.values(), key=lambda item: (-item[0], item[1]))]


def _table_query(
    index: SearchIndex,
    query: str,
    mode: str,
    *,
    scope: str | None,
    kind: str | None,
    limit: int = 200,
) -> list[str]:
    pointer = index.store.projection()
    if pointer is None:
        raise RuntimeError("retrieval projection is absent")
    table = index._table(pointer)  # noqa: SLF001 - evaluation needs the exact pinned table.
    search = (
        table.search(query, query_type="fts")
        if mode == "fulltext"
        else table.search(index.embedder.embed_query(query), query_type="vector")
    )
    where = _where(scope, kind)
    if where is not None:
        search = search.where(where, prefilter=True)
    return _rank(search.limit(limit).to_list())[:10]


def _baseline(store: Any, query: str, scope: str | None, kind: str | None) -> list[str]:
    connection = sqlite3.connect(store.home / "workshop.sqlite3")
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "WITH active AS ("
            " SELECT a.name, a.scope, a.kind, a.summary, a.tags,"
            " e.seq AS adoption, e.status"
            " FROM assets a JOIN asset_events e ON e.ref = a.ref"
            " WHERE e.status IN ('trial', 'stable')"
            " AND e.seq = (SELECT MAX(x.seq) FROM asset_events x WHERE x.ref = a.ref)),"
            " ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY scope, name"
            " ORDER BY adoption DESC) AS rank FROM active)"
            " SELECT name, scope, kind, summary, tags FROM ranked WHERE rank = 1"
        ).fetchall()
    finally:
        connection.close()
    words = query.casefold().split()
    scored = []
    for row in rows:
        if scope is not None and row["scope"] != scope:
            continue
        if kind is not None and row["kind"] != kind:
            continue
        tags = json.loads(row["tags"])
        text = " ".join([row["name"], row["summary"], *tags]).casefold()
        score = sum(word in text for word in words)
        if words and score == 0:
            continue
        scored.append((score, row["name"], row["scope"]))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [name for _score, name, _scope in scored[:10]]


def _recall(ranked: list[str], relevant: dict[str, int]) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:10]) & set(relevant)) / len(relevant)


def _ndcg(ranked: list[str], relevant: dict[str, int]) -> float:
    if not relevant:
        return 0.0
    dcg = sum(relevant.get(name, 0) / math.log2(index + 2) for index, name in enumerate(ranked[:5]))
    ideal = sum(
        grade / math.log2(index + 2)
        for index, grade in enumerate(sorted(relevant.values(), reverse=True)[:5])
    )
    return dcg / ideal if ideal else 0.0


def _metrics(results: dict[str, list[str]], queries: list[dict[str, Any]]) -> dict[str, Any]:
    values = []
    for query in queries:
        relevant = {item["name"]: int(item["grade"]) for item in query["relevant"]}
        if not relevant:
            continue
        ranked = results[query["id"]]
        values.append(
            {
                "id": query["id"],
                "category": query["category"],
                "recall": _recall(ranked, relevant),
                "ndcg": _ndcg(ranked, relevant),
            }
        )
    categories: dict[str, list[dict[str, Any]]] = {}
    for value in values:
        categories.setdefault(value["category"], []).append(value)
    return {
        "queries": len(values),
        "recall_at_10": round(sum(item["recall"] for item in values) / len(values), 4) if values else None,
        "ndcg_at_5": round(sum(item["ndcg"] for item in values) / len(values), 4) if values else None,
        "by_category": {
            key: {
                "queries": len(items),
                "recall_at_10": round(sum(item["recall"] for item in items) / len(items), 4),
                "ndcg_at_5": round(sum(item["ndcg"] for item in items) / len(items), 4),
            }
            for key, items in sorted(categories.items())
        },
        "per_query": values,
    }


def _search_all(
    index: SearchIndex,
    store: Any,
    queries: list[dict[str, Any]],
    modes: tuple[str, ...],
    *,
    scope: str | None = None,
    kind: str | None = None,
) -> tuple[dict[str, dict[str, list[str]]], dict[str, float]]:
    results = {mode: {} for mode in modes}
    timings = dict.fromkeys(modes, 0.0)
    for query in queries:
        for mode in modes:
            started = time.perf_counter()
            if mode == "baseline":
                ranked = _baseline(store, query["query"], scope, kind)
            elif mode == "hybrid":
                matches = index.page(query["query"], limit=10, scope=scope, kind=kind)["matches"]
                ranked = [item["name"] for item in matches]
            else:
                ranked = _table_query(index, query["query"], mode, scope=scope, kind=kind)
            timings[mode] += time.perf_counter() - started
            results[mode][query["id"]] = ranked
    return results, timings


def _evaluate(root: Path) -> dict[str, Any]:
    corpus = json.loads(FIXTURE.read_text(encoding="utf-8"))
    model_cache = Path(os.environ.get("ASTROFAIRY_MODEL_CACHE", ".cache/fastembed")).resolve()
    run_root = root / datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")
    run_root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    full = _build(run_root / "full", corpus, metadata_only=False, model_cache=model_cache)
    metadata = _build(run_root / "metadata", corpus, metadata_only=True, model_cache=model_cache)
    built = time.perf_counter() - started
    try:
        index = full.library.search_index
        started = time.perf_counter()
        projection = index.refresh()
        refresh_seconds = time.perf_counter() - started
        metadata_index = metadata.library.search_index
        started = time.perf_counter()
        metadata_index.refresh()
        metadata_refresh_seconds = time.perf_counter() - started
        holdout = corpus["holdout"]
        started = time.perf_counter()
        first = index.page(holdout[0]["query"], limit=10)
        first_query_seconds = time.perf_counter() - started
        modes = ("hybrid", "fulltext", "vector", "baseline")
        results, timings = _search_all(index, full.store, holdout, modes)
        tuning_results, tuning_timings = _search_all(index, full.store, corpus["tuning"], modes)
        metadata_results, metadata_timings = _search_all(metadata_index, metadata.store, holdout, ("hybrid",))
        filters = []
        for case in corpus["filter_cases"]:
            rows = index.page(case["query"], limit=10, scope=case["scope"], kind=case["kind"])["matches"]
            wrong = [
                item["name"]
                for item in rows
                if (case["scope"] is not None and item["scope"] != case["scope"])
                or (case["kind"] is not None and item["kind"] != case["kind"])
            ]
            filters.append({"id": case["id"], "returned": len(rows), "violations": wrong})
        negatives = {}
        for query in corpus["negative"]:
            ranked = [item["name"] for item in index.page(query["query"], limit=10)["matches"]]
            negatives[query["id"]] = {"query": query["query"], "top3": ranked[:3]}
        metrics = {mode: _metrics(result, holdout) for mode, result in results.items()}
        tuning_metrics = {mode: _metrics(result, corpus["tuning"]) for mode, result in tuning_results.items()}
        body_queries = [query for query in holdout if query["category"] == "body_only"]
        body_metrics = {
            "full_hybrid": _metrics(results["hybrid"], body_queries),
            "metadata_hybrid": _metrics(metadata_results["hybrid"], body_queries),
        }
        return {
            "format": 1,
            "evaluated_at": datetime.now(UTC).isoformat(),
            "run_root": str(run_root),
            "fixture": {
                "path": str(FIXTURE.relative_to(FIXTURE.parents[2])),
                "sha256": _digest_file(FIXTURE),
                "assets": len(corpus["assets"]),
                "holdout_positive": len(holdout),
                "holdout_negative": len(corpus["negative"]),
                "tuning": len(corpus["tuning"]),
            },
            "host": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
            },
            "model": {
                "profile": PROFILE_ID,
                "model": PROFILE["embedding"]["model"],
                "revision": PROFILE["embedding"]["revision"],
                "embedding": "real local FastEmbed multilingual-e5-large ONNX",
            },
            "projection": projection,
            "build_seconds": round(built, 3),
            "refresh_seconds": round(refresh_seconds, 3),
            "metadata_refresh_seconds": round(metadata_refresh_seconds, 3),
            "first_query_seconds": round(first_query_seconds, 3),
            "warm_query_seconds": {
                mode: round(value / max(1, len(holdout)), 4) for mode, value in timings.items()
            },
            "tuning_warm_query_seconds": {
                mode: round(value / max(1, len(corpus["tuning"])), 4)
                for mode, value in tuning_timings.items()
            },
            "metadata_warm_query_seconds": {
                mode: round(value / max(1, len(holdout)), 4) for mode, value in metadata_timings.items()
            },
            "peak_rss_kb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "holdout": metrics,
            "tuning": tuning_metrics,
            "body_benefit": body_metrics,
            "filters": filters,
            "negative_queries": negatives,
            "negative_note": (
                "Retrieval returns nearest candidates for no-match queries; automatic applicability or "
                "no-such-method refusal is a host/model decision, not a retrieval metric."
            ),
            "first_query_result": [item["name"] for item in first["matches"]],
            "unknown": {
                "host_model_trajectory": (
                    "No host conversation/model execution is available to this local runner; "
                    "behavioral adherence, first useful feedback, human intervention and cost are unknown."
                ),
                "cold_model_preparation": (
                    "The fixed model was already present in the local cache; a first-time model download "
                    "and cold process setup were not repeated."
                ),
            },
        }
    finally:
        full.store.close()
        metadata.store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the frozen local retrieval corpus with the real model"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(".evaluation/optimization-implementation/retrieval-eval"),
    )
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = _evaluate(arguments.root)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
