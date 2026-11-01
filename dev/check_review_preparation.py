from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/reviews"


def load() -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = json.loads((REVIEW / "system-inventory.json").read_text(encoding="utf-8"))
    catalog = json.loads((REVIEW / "authority-sources.json").read_text(encoding="utf-8"))
    if not isinstance(inventory, dict) or not isinstance(catalog, dict):
        raise TypeError("Preparation data must contain JSON objects")
    return inventory, catalog


def frozen_files(commit: str) -> dict[str, bytes]:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Review baseline must name a full Git commit")
    git = shutil.which("git")
    if git is None:
        raise ValueError("Git is required to verify the frozen review baseline")
    tree = subprocess.run(
        [git, "ls-tree", "-r", "--name-only", "-z", commit],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return {
        path: subprocess.run(
            [git, "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=True
        ).stdout
        for path in tree.stdout.decode("utf-8").split("\0")
        if path
    }


def validate(inventory: dict[str, Any], catalog: dict[str, Any], *, snapshots: bool) -> list[str]:
    errors = []
    objects = inventory["objects"]
    ids = [item["id"] for item in objects]
    sources = {source["id"]: source for source in catalog["sources"]}
    if len(ids) != len(set(ids)) or len(sources) != len(catalog["sources"]):
        errors.append("Duplicate object or authority source id")
    baseline = {item["path"]: item for item in inventory["baseline_files"]}
    try:
        frozen = frozen_files(inventory["baseline_commit"])
    except (ValueError, subprocess.CalledProcessError) as exc:
        return [f"Cannot read frozen review baseline: {exc}"]
    if set(frozen) != set(baseline):
        errors.append("Frozen commit files differ from the registered inventory")
    signature = json.dumps(
        [(item["path"], item["sha256"]) for item in inventory["baseline_files"]],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if hashlib.sha256(signature).hexdigest() != inventory["baseline_manifest_sha256"]:
        errors.append("Frozen baseline manifest is incomplete or altered")
    if inventory["mandatory_steps"] != [f"Q{index:02}" for index in range(1, 9)]:
        errors.append("Full-object industry comparison obligations are incomplete")
    for item in objects:
        if not item["sources"] or not item["comparison_question"] or not item["review_facets"]:
            errors.append(f"Missing full-review obligation: {item['id']}")
        if set(item["sources"]) - sources.keys():
            errors.append(f"Unknown authority source: {item['id']}")
        for anchor in item["anchors"]:
            if anchor["path"] not in frozen and not any(
                name.startswith(anchor["path"] + "/") for name in frozen
            ):
                errors.append(f"Missing implementation anchor: {item['id']} {anchor['path']}")
            if anchor["symbol"] and not any(
                symbol["name"] == anchor["symbol"]
                for symbol in baseline.get(anchor["path"], {}).get("symbols", [])
            ):
                errors.append(f"Unknown baseline symbol: {item['id']} {anchor['symbol']}")
    for entry in baseline.values():
        path = Path(entry["path"])
        if not entry["objects"] or set(entry["objects"]) - set(ids):
            errors.append(f"Unregistered baseline file: {entry['path']}")
        data = frozen.get(entry["path"])
        if data is None or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            errors.append(f"Frozen baseline content missing or altered: {entry['path']}")
        elif path.suffix == ".py":
            ast.parse(data.decode("utf-8"))
    for facet, object_ids in inventory["review_coverage"].items():
        if not object_ids or set(object_ids) - set(ids):
            errors.append(f"Missing review-facet coverage: {facet}")
        if set(object_ids) != {item["id"] for item in objects if facet in item["review_facets"]}:
            errors.append(f"Review-facet mapping drift: {facet}")
    if set(inventory["review_coverage"]) != {f"R{index:02}" for index in range(1, 17)}:
        errors.append("Review facets are not fully registered")
    for source in sources.values():
        materials = [item for item in source["materials"] if item["status"] == "retrieved"]
        if not materials:
            errors.append(f"No accessible primary material: {source['id']}")
        for material in materials:
            if not re.fullmatch(r"[a-f0-9]{64}", material["sha256"]):
                errors.append(f"Invalid source digest: {source['id']}")
            if snapshots:
                snapshot = ROOT / material["snapshot"]
                if (
                    not snapshot.is_file()
                    or hashlib.sha256(snapshot.read_bytes()).hexdigest() != material["sha256"]
                ):
                    errors.append(f"Source snapshot missing or altered: {source['id']} {material['name']}")
    return errors


def views(inventory: dict[str, Any], catalog: dict[str, Any]) -> dict[Path, str]:
    lines = [
        "# 全量架构、机制及组合台账",
        "",
        "生成视图。定义单源为 system-inventory.json。",
        "更新后运行 `python dev/check_review_preparation.py --render`。",
        "所有对象均须完成行业调查与对标。本表登记范围和进度。状态不代表达标。",
        "",
        "A 为整体/子架构。M 为机制。C 为组合路径。U 为从愿景导出的待证责任。",
        "文件与符号登记用于发现漏登记。语义覆盖仍需正式复核。",
        "",
        "基线 `" + inventory["baseline_commit"] + "`。",
        "候选权威源详情见[来源目录](authority-sources.md)。",
        "",
    ]
    reviewed = [item for item in inventory["objects"] if item["evidence"]]
    if reviewed:
        lines += ["## 已有轮次证据", "", "| 对象 | 状态 | 证据 |", "|---|---|---|"]
        for item in reviewed:
            evidence = "、".join(f"[轮次记录]({path})" for path in item["evidence"])
            lines.append(f"| {item['id']} | {item['status']} | {evidence} |")
        lines += [""]
    for kind in ("architecture", "mechanism", "composition", "requirement probe"):
        lines += [
            "## " + kind,
            "",
            "| 编号与对象 | 当前行为/边界 | 对标问题 | 复核面 / 权威源 | 定位 |",
            "|---|---|---|---|---|",
        ]
        for item in inventory["objects"]:
            if item["kind"] != kind:
                continue
            anchors = "、".join(
                "["
                + (anchor["symbol"] or anchor["path"].split("/")[-1])
                + "](../../"
                + anchor["path"]
                + "#L"
                + str(anchor["line"])
                + ")"
                for anchor in item["anchors"]
            )
            lines.append(
                f"| {item['id']} {item['title']} | {item['current']} | {item['comparison_question']} | "
                + " ".join(item["review_facets"])
                + " / "
                + " ".join(item["sources"])
                + " | "
                + anchors
                + " |"
            )
        lines += [""]
    lines += ["## 文件覆盖索引", "", "| 初版文件 | 负责机制 | 符号数 |", "|---|---|---|"]
    lines += [
        f"| {item['path']} | {' '.join(item['objects'])} | {len(item['symbols'])} |"
        for item in inventory["baseline_files"]
    ]
    lines += [
        "",
        "以上是登记范围。不代表已完成审查。实际读取、判断、反例和证据见[轮次索引](INDEX.md)。",
        "各对象状态与证据引用以 JSON 为准。未裁定对象仍承担完整对标义务。",
        "",
    ]
    sources = [
        "# 权威来源目录",
        "",
        "生成视图。元数据单源为 authority-sources.json。",
        "已取得材料用于准备取证。适用性、条款、成熟度与对标结论尚待正式复核。",
        "ISO 目录/摘要不代表取得标准全文。官方实现自述不替代实际效果验证。",
        "",
        "| 编号 | 一手来源及类别 | 固定版本 / 取得原件数 | 用途及限制 |",
        "|---|---|---|---|",
    ]
    for source in catalog["sources"]:
        count = sum(item["status"] == "retrieved" for item in source["materials"])
        version = source.get("version", "未取得")
        if re.fullmatch(r"[a-f0-9]{40}", version):
            version = version[:12]
        elif version.startswith("URL version"):
            version = "URL 版本。其余依取得时间与 SHA256 定位"
        sources.append(
            f"| {source['id']} | [{source['title']}]({source['url']})。"
            f"{source['authority']}。{source['kind']} | "
            + version
            + f" / {count} | {source['use']}。{source['limit']} |"
        )
    sources += [
        "",
        "原始页、响应目标、SHA256、时间和固定提交见 JSON。原件缓存在本机忽略目录。未随公开分发复制。",
        "可变 URL 的历史内容需要保留原件才能复验。摘要只能说明内容身份。",
        "相同 URL 不保证今后提供相同内容。",
        "正式引用必须补上具体条款/源码位置、支持的主张和适用条件。不能只附项目主页。",
        "",
    ]
    return {
        REVIEW / "system-inventory.md": "\n".join(lines),
        REVIEW / "authority-sources.md": "\n".join(sources),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate review preparation coverage and generated views")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify-snapshots", action="store_true")
    arguments = parser.parse_args()
    inventory, catalog = load()
    errors = validate(inventory, catalog, snapshots=arguments.verify_snapshots)
    for path, content in views(inventory, catalog).items():
        if arguments.render:
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            errors.append("Generated view drift: " + str(path.relative_to(ROOT)))
    for error in errors:
        print(error)
    if errors:
        return 1
    print(
        f"Prepared {len(inventory['objects'])} objects, {len(inventory['baseline_files'])} baseline files "
        f"and {len(catalog['sources'])} primary source families against the frozen Git baseline; "
        "this does not assess repaired live code."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
