from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ("codex", "claude-code", "cursor", "github-copilot", "gemini-cli")


def run(arguments: list[str], directory: Path, env: dict[str, str], data: Any = None) -> Any:
    result = subprocess.run(
        arguments,
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        input=json.dumps(data) if data is not None else None,
        check=True,
        timeout=60,
    )
    return json.loads(result.stdout)


def probe(node: Path, cli: Path, directory: Path, agent: str, env: dict[str, str]) -> dict[str, Any]:
    directory.mkdir()
    git = shutil.which("git")
    if git is None:
        raise FileNotFoundError("Git is required for isolated project fixtures")
    subprocess.run([git, "init", "--quiet", str(directory)], check=True, env=env)
    installation = run(
        [
            str(node),
            str(cli),
            "add",
            str(ROOT),
            "--skill",
            "astrofairy",
            "--agent",
            agent,
            "--copy",
            "--yes",
            "--json",
        ],
        directory,
        env,
    )
    launchers = list(directory.glob("**/skills/astrofairy/scripts/fairy.py"))
    if len(launchers) != 1:
        raise ValueError(f"Expected one copied skill for {agent}: {launchers}")
    launcher = launchers[0]
    home = directory / "state"
    command = [sys.executable, "-I", "-S", str(launcher), "--home", str(home)]
    doctor = run([*command, "doctor"], directory, env)
    if not doctor["ready"] or home.exists():
        raise ValueError("Read-only readiness check failed")
    packet = run([*command, "start", "--request", "Create a brief installation result"], directory, env)
    task = packet["task"]

    def submit(data: dict[str, Any]) -> Any:
        return run([*command, "submit", task], directory, env, data)

    request = submit({"op": "request", "purpose": "Write the installation brief"})
    content = "The copied skill produced this brief without its source checkout or site-packages."
    report = submit({"op": "report", "call": request["call"], "text": content, "name": "brief.md"})
    ref = report["ref"]
    submit({"op": "publish", "ref": ref})
    submit({"op": "check"})
    submit(
        {
            "op": "review",
            "criterion": "goal",
            "verdict": "pass",
            "basis": "This scripted fixture requests a brief installation result and publishes that brief.",
            "evidence": [ref],
        }
    )
    delivery = submit({"op": "close", "outcome": "complete"})
    if Path(delivery["artifact_path"]).read_text(encoding="utf-8") != content:
        raise ValueError("Delivered content does not match the fixture")
    receipt = json.loads(Path(delivery["receipt_path"]).read_text(encoding="utf-8"))
    if {review["producer"] for review in receipt["reviews"]} != {"model", "tool:nonempty"}:
        raise ValueError("Receipt producer attribution is incorrect")
    return {
        "agent": agent,
        "installation": installation,
        "launcher": str(launcher.relative_to(ROOT)),
        "doctor": doctor,
        "delivery": delivery,
        "isolation": "Python -I -S; no site-packages",
        "scope": "Installer layout and scripted protocol fixture; native agent/model not exercised",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Exercise the real skills CLI in isolated project fixtures")
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--skills-cli", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / ".evaluation/installation")
    arguments = parser.parse_args()
    output = arguments.out.resolve()
    if not output.is_relative_to(ROOT) or output == ROOT:
        parser.error("Keep installation fixtures inside an AstroFairy subdirectory")
    output.mkdir(parents=True, exist_ok=True)
    batch = Path(tempfile.mkdtemp(prefix="run-", dir=output))
    temporary = batch / "tmp"
    temporary.mkdir()
    env = {
        **os.environ,
        "DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "TMPDIR": str(temporary),
        "XDG_CACHE_HOME": str(batch / "cache"),
    }
    results = []
    for agent in AGENTS:
        results.append(
            probe(arguments.node.resolve(), arguments.skills_cli.resolve(), batch / agent, agent, env)
        )
        print(f"{agent}: installed copy and isolated task delivery passed", flush=True)
    (output / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
