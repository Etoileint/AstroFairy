from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from astrofairy import Workshop
from astrofairy._presentation import read_document
from astrofairy._search import SearchIndex


def _complete(
    workshop: Workshop, request: str, text: str, *, role: str = "main", read_asset: str | None = None
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    task = workshop.start(request)
    packet = workshop.next(task)
    asset_read = workshop.invoke(task, "asset.read", {"ref": read_asset}) if read_asset is not None else None
    call = workshop.submit(task, {"op": "request", "purpose": "Produce a concise evidence-based result"})
    output = workshop.submit(task, {"op": "report", "call": call["call"], "text": text, "path": "result.md"})
    workshop.submit(
        task,
        {
            "op": "publish",
            "members": [
                {
                    "ref": output["ref"],
                    "path": output["path"],
                    "bytes": output["bytes"],
                    "media_type": output["media_type"],
                    "role": role,
                }
            ],
        },
    )
    if packet["provisional"]:
        workshop.submit(
            task,
            {
                "op": "revise",
                "goal": packet["goal"],
                "criteria": packet["criteria"],
                "reason": "Refine the provisional agreement for this evaluation task",
                "required_roles": [role],
            },
        )
    workshop.submit(task, {"op": "check"})
    workshop.submit(
        task,
        {
            "op": "review",
            "criterion": "goal",
            "verdict": "pass",
            "basis": "The recorded result answers the stated request; this is an evaluation fixture judgment",
        },
    )
    workshop.submit(task, {"op": "close", "outcome": "complete"})
    return task, output, asset_read


def _validate(workshop: Workshop, package: dict[str, Any]) -> tuple[str, str]:
    ref = workshop.library.propose(package)
    task = workshop.validation_task(ref)
    workshop.submit(task, {"op": "check"})
    workshop.submit(
        task,
        {
            "op": "review",
            "criterion": "asset-fitness",
            "verdict": "pass",
            "basis": "Evaluation fixture validated through the real adoption policy; not a user study",
        },
    )
    workshop.submit(task, {"op": "close", "outcome": "complete"})
    workshop.library.adopt(ref, task, "stable")
    return ref, task


def _package(name: str, content: str, summary: str, source_task: str) -> dict[str, Any]:
    return {
        "name": name,
        "scope": "personal",
        "kind": "guide",
        "summary": summary,
        "tags": ["brief", "evidence"],
        "content": content,
        "evidence": [{"source": f"task:{source_task}", "note": "Observed in the evaluation task"}],
    }


def _run(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    model_cache = Path(os.environ.get("ASTROFAIRY_MODEL_CACHE", ".cache/fastembed")).resolve()
    workshop = Workshop(root / "state")
    workshop.library.search_index = SearchIndex(workshop.store, model_cache=model_cache)
    started = time.perf_counter()
    source, _, _ = _complete(
        workshop,
        "Draft a short brief from a source note",
        "State the audience, the decision and the evidence. Keep the brief to one page.",
    )
    workshop.submit(
        source, {"op": "feedback", "kind": "positive", "text": "The one-page structure worked for review"}
    )
    maintenance = workshop.submit(source, {"op": "learn"})["learning_task"]
    locator = workshop.state(maintenance).inputs[0]["source_document"]
    page = read_document(workshop.store.home, locator["document"], task=source, pointer="/feedback/0")
    feedback = json.loads(page["text"])
    package = _package(
        "source-brief-method",
        "Lead with audience and decision, then evidence, then limits. Keep the main brief to one page.",
        "One-page source brief method",
        source,
    )
    asset, _validation = _validate(workshop, package)
    formed = time.perf_counter() - started

    started = time.perf_counter()
    first_page = workshop.library.search_page("one page source brief method", limit=8, refresh=True)
    search_seconds = time.perf_counter() - started
    first_names = [item["name"] for item in first_page["matches"]]
    reuse_task, _reuse_output, read = _complete(
        workshop,
        "Use the adopted one-page brief method for a new source note",
        "A new brief",
        read_asset=asset,
    )
    reuse_seconds = time.perf_counter() - started
    reuse_resources = workshop.next(reuse_task)["resources"]

    revision_started = time.perf_counter()
    revised_ref, _revision_validation = _validate(
        workshop,
        _package(
            "source-brief-method",
            (
                "Lead with audience and decision, then evidence, limits and a named owner. "
                "Keep the brief to one page."
            ),
            "One-page source brief method, revised",
            source,
        ),
    )
    revised_page = workshop.library.search_page("one page source brief method", limit=8, refresh=True)
    revision_seconds = time.perf_counter() - revision_started
    head = workshop.library.head("personal", "source-brief-method")

    retirement_started = time.perf_counter()
    workshop.library.retire(revised_ref)
    retired_page = workshop.library.search_page("one page source brief method", limit=8, refresh=True)
    retirement_seconds = time.perf_counter() - retirement_started
    remaining_head = workshop.library.head("personal", "source-brief-method")

    no_change_started = time.perf_counter()
    no_change = workshop.learning_task(source)
    note_call = workshop.submit(
        no_change, {"op": "request", "purpose": "Decide whether to change the method"}
    )
    note = workshop.submit(
        no_change,
        {
            "op": "report",
            "call": note_call["call"],
            "text": "No change: the observed feedback supports the current method.",
            "path": "decision.md",
        },
    )
    workshop.submit(
        no_change,
        {
            "op": "publish",
            "members": [
                {
                    "ref": note["ref"],
                    "path": note["path"],
                    "bytes": note["bytes"],
                    "media_type": note["media_type"],
                    "role": "decision",
                }
            ],
        },
    )
    workshop.submit(no_change, {"op": "check"})
    workshop.submit(
        no_change,
        {
            "op": "review",
            "criterion": "grounded",
            "verdict": "pass",
            "basis": "The recorded feedback supports no change; this is an evaluation fixture judgment",
        },
    )
    workshop.submit(no_change, {"op": "close", "outcome": "complete"})
    no_change_seconds = time.perf_counter() - no_change_started
    return {
        "format": 1,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "model": "real FastEmbed multilingual-e5-large ONNX via SearchIndex",
        "source_task": source,
        "maintenance_task": maintenance,
        "feedback": feedback,
        "asset": asset,
        "formation_seconds": round(formed, 3),
        "formation_resources": workshop.next(source)["resources"],
        "reuse_search_seconds": round(search_seconds, 3),
        "reuse_search_first_names": first_names,
        "reuse_asset_read": {"status": read["status"], "asset_ref": read.get("result", {}).get("asset_ref")},
        "reuse_task": reuse_task,
        "reuse_seconds": round(reuse_seconds, 3),
        "reuse_resources": reuse_resources,
        "revision_seconds": round(revision_seconds, 3),
        "revision_head": head,
        "revision_search_names": [item["name"] for item in revised_page["matches"]],
        "retirement_seconds": round(retirement_seconds, 3),
        "remaining_head": remaining_head,
        "retirement_search_names": [item["name"] for item in retired_page["matches"]],
        "no_change_seconds": round(no_change_seconds, 3),
        "no_change_outcome": workshop.state(no_change).outcome,
        "source_history_unchanged": workshop.state(source).outcome == "complete",
        "unknown": {
            "human_review": (
                "Semantic pass decisions are executor-authored fixture judgments, not human review."
            ),
            "long_term_benefit": (
                "One local formation/reuse/revision/retirement cycle does not establish "
                "long-term or team benefit."
            ),
            "host_model_cost": (
                "No host model conversation, token count or currency billing is available locally."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the learning formation/reuse/revision/retirement path"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(".evaluation/optimization-implementation/learning-eval"),
    )
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = _run(arguments.root)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
