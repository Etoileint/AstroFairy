from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from astrofairy._capabilities import atomic_write
from astrofairy._contracts import (
    ResourcePolicy,
    canonical,
    object_value,
    parse_json,
    runtime_status,
    schema,
    task_spec_value,
)
from astrofairy._delivery import status as delivery_status
from astrofairy._documents import audit_document
from astrofairy._errors import FairyError
from astrofairy._library import KINDS
from astrofairy._limits import LIMITS
from astrofairy._maintenance import audit_state, backup_state, restore_state, verify_backup
from astrofairy._presentation import controls, encode_response, read_document
from astrofairy._runtime import Workshop
from astrofairy._search import model_cache_path
from astrofairy._search import observations as search_observations
from astrofairy._store import sqlite_runtime


def _input(path: str) -> Any:
    if path == "-":
        data = sys.stdin.buffer.read(LIMITS.command_json_bytes + 1)
    else:
        with Path(path).open("rb") as stream:
            data = stream.read(LIMITS.command_json_bytes + 1)
    if len(data) > LIMITS.command_json_bytes:
        raise FairyError("limit", "Input exceeds the byte budget")
    return parse_json(data.decode("utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astrofairy")
    parser.add_argument(
        "--home",
        type=Path,
        default=Path(os.environ.get("ASTROFAIRY_HOME", Path.home() / ".local/share/astrofairy")),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema")
    doctor = commands.add_parser("doctor")
    doctor.add_argument(
        "--verify-search",
        action="store_true",
        help="Stream-verify the fixed model files without downloading, indexing or inference",
    )
    commands.add_parser("todos", help="List deferred learning decisions across all tasks")
    governance = commands.add_parser("governance", help="List adopted governance assets by scope")
    governance.add_argument("--scope", choices=["personal", "team"])
    commands.add_parser("audit-state", help="Read-only audit of recorded state and retained documents")
    backup = commands.add_parser("backup", help="Back up recorded state into a new directory")
    backup.add_argument("--out", required=True, type=Path)
    backup.add_argument(
        "--deadline",
        type=int,
        default=LIMITS.backup_deadline_seconds,
        help="Per-database backup progress deadline in seconds",
    )
    verify = commands.add_parser("verify-backup", help="Verify a completed recorded-state backup")
    verify.add_argument("directory", type=Path)
    restore = commands.add_parser("restore", help="Restore verified recorded state into a fresh home")
    restore.add_argument("directory", type=Path)
    restore.add_argument("--out", required=True, type=Path)
    read = commands.add_parser("read", help="Read a free fragment of an immutable response document")
    read.add_argument("document")
    read.add_argument("--task")
    read.add_argument("--pointer", default="")
    read.add_argument("--offset", type=int, default=0)
    read.add_argument("--limit", type=int, default=LIMITS.document_read_characters)
    audit = commands.add_parser("audit-document", help="Verify every reachable document block")
    audit.add_argument("document")
    audit.add_argument("--task")
    catalog = commands.add_parser("capabilities")
    catalog.add_argument("--query", default="")
    catalog.add_argument("--limit", type=int, default=LIMITS.catalog_default_limit)
    catalog.add_argument("--cursor")
    catalog.add_argument("--name", help="Read one complete current tool definition")
    start = commands.add_parser("start")
    start.add_argument("--request", required=True)
    start.add_argument("--input", action="append", type=Path, default=[])
    start.add_argument("--resources", help="JSON resource policy; defaults are shown by schema")
    start.add_argument("--read-only", action="store_true")
    start.add_argument("--spec", help="JSON with goal, criteria and assumptions")
    for name in ("next", "inspect", "deliver", "submit"):
        child = commands.add_parser(name)
        child.add_argument("task")
        if name == "inspect":
            inspection = child.add_mutually_exclusive_group()
            inspection.add_argument("--history", action="store_true")
            inspection.add_argument("--contract", help="Read one definition recorded for this task")
        if name == "deliver":
            child.add_argument("--expected-seq", type=int)
            child.add_argument(
                "--repair",
                action="store_true",
                help="Replace an invalid derived export after validating a fresh staging bag",
            )
        if name == "submit":
            child.add_argument("--file", default="-", help="Read a JSON command from file or stdin")
    prepare = commands.add_parser(
        "prepare-delivery",
        help="Capture explicit workspace members, publish the snapshot and run mechanical checks",
    )
    prepare.add_argument("task")
    prepare.add_argument("--members", required=True, help="JSON member plan")
    prepare.add_argument("--expected-seq", type=int)
    assets = commands.add_parser("assets").add_subparsers(dest="asset_command", required=True)
    assets.add_parser(
        "prepare",
        help="Explicitly prepare and verify the fixed retrieval model without building an index",
    )
    search = assets.add_parser("search")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--limit", type=int, default=LIMITS.search_page_default_limit)
    search.add_argument("--cursor")
    search.add_argument("--scope", choices=["personal", "team"])
    search.add_argument("--kind", choices=sorted(KINDS))
    search.add_argument(
        "--refresh",
        action="store_true",
        help="Explicitly build the retrieval projection (may prepare the fixed model)",
    )
    propose = assets.add_parser("propose")
    propose.add_argument("file")
    importing = assets.add_parser("import")
    importing.add_argument("file", type=Path)
    for name in ("inspect", "validate", "adopt", "retire", "export"):
        child = assets.add_parser(name)
        child.add_argument("ref")
        if name == "adopt":
            child.add_argument("--task", required=True)
            child.add_argument("--status", choices=["trial", "stable"], default="trial")
        if name == "export":
            child.add_argument("--out", required=True, type=Path)
    return parser


def _run(arguments: argparse.Namespace) -> dict[str, Any]:
    if arguments.command == "schema":
        return schema()
    if arguments.command == "audit-state":
        return audit_state(arguments.home)
    if arguments.command == "backup":
        return backup_state(arguments.home, arguments.out, deadline_seconds=arguments.deadline)
    if arguments.command == "verify-backup":
        return verify_backup(arguments.directory)
    if arguments.command == "restore":
        return restore_state(arguments.directory, arguments.out)
    if arguments.command == "audit-document":
        return audit_document(arguments.home, arguments.document, task=arguments.task)
    if arguments.command == "read":
        return read_document(
            arguments.home,
            arguments.document,
            task=arguments.task,
            pointer=arguments.pointer,
            offset=arguments.offset,
            limit=arguments.limit,
        )
    if arguments.command == "doctor":
        home = arguments.home.resolve()
        ancestor = home
        while not ancestor.exists():
            ancestor = ancestor.parent
        writable = ancestor.is_dir() and os.access(ancestor, os.W_OK | os.X_OK)
        supported = sys.version_info >= (3, 12)
        incomplete = os.path.lexists(home / "restore.pending")
        runtime = runtime_status()
        sqlite = sqlite_runtime()
        delivery = delivery_status()
        return {
            "ready": supported
            and writable
            and not incomplete
            and runtime["ready"]
            and sqlite["ready"]
            and delivery["ready"],
            "restore_incomplete": incomplete,
            "runtime": runtime,
            "sqlite": sqlite,
            "delivery": delivery,
            "search": search_observations(model_cache_path(home), verify=arguments.verify_search),
            "python": sys.version.split()[0],
            "requires_python": ">=3.12",
            "home": str(home),
            "home_exists": home.exists(),
            "writable_parent": writable,
            "model": "conversation-host",
            "persistence": "The host must retain this directory between sessions",
        }
    spec = None
    resources = None
    if arguments.command == "start":
        spec = object_value(_input(arguments.spec)) if arguments.spec is not None else {}
        resources = ResourcePolicy.parse(_input(arguments.resources)) if arguments.resources else None
        task_spec_value(
            arguments.request, spec, resources, ["reason", "read"] if arguments.read_only else None
        )
    with Workshop(arguments.home) as workshop:
        if arguments.command == "todos":
            return {"todos": workshop.todos()}
        if arguments.command == "governance":
            return workshop.governance(arguments.scope)
        if arguments.command == "prepare-delivery":
            return workshop.prepare_delivery(
                arguments.task, _input(arguments.members), arguments.expected_seq
            )
        if arguments.command == "capabilities":
            if arguments.name is not None:
                return workshop.describe(arguments.name)
            return workshop.catalog(arguments.query, arguments.limit, arguments.cursor)
        if arguments.command == "start":
            task = workshop.start(
                arguments.request,
                spec=spec,
                resources=resources,
                effects=["reason", "read"] if arguments.read_only else None,
                inputs=arguments.input,
            )
            return workshop.next(task)
        if arguments.command == "next":
            return workshop.next(arguments.task)
        if arguments.command == "inspect":
            if arguments.contract is not None:
                return workshop.inspect_contract(arguments.task, arguments.contract)
            return workshop.inspect(arguments.task, history=arguments.history)
        if arguments.command == "deliver":
            return workshop.deliver(
                arguments.task, expected_seq=arguments.expected_seq, repair=arguments.repair
            )
        if arguments.command == "submit":
            return workshop.submit(arguments.task, object_value(_input(arguments.file)))
        operation = arguments.asset_command
        library = workshop.library
        if operation == "prepare":
            return {
                "preparation": library.prepare(),
                "projection": {"state": "not_built"},
                "recovery": "assets search --refresh",
            }
        if operation == "search":
            return library.search_page(
                arguments.query,
                arguments.limit,
                arguments.scope,
                arguments.kind,
                arguments.cursor,
                refresh=arguments.refresh,
            )
        if operation == "propose":
            ref = library.propose(object_value(_input(arguments.file)))
            return {"ref": ref, "status": "candidate", "validation_task": workshop.validation_task(ref)}
        if operation == "import":
            with arguments.file.open("rb") as stream:
                data = stream.read(LIMITS.command_json_bytes + 1)
            if len(data) > LIMITS.command_json_bytes:
                raise FairyError("limit", "Asset import exceeds its byte budget")
            ref = library.import_bundle(data)
            return {"ref": ref, "status": "candidate", "validation_task": workshop.validation_task(ref)}
        if operation == "inspect":
            return {"package": library.get(arguments.ref), "status": library.status(arguments.ref)}
        if operation == "validate":
            return {"validation_task": workshop.validation_task(arguments.ref)}
        if operation == "adopt":
            library.adopt(arguments.ref, arguments.task, arguments.status)
            return {"ref": arguments.ref, "status": library.status(arguments.ref)}
        if operation == "retire":
            library.retire(arguments.ref)
            return {"ref": arguments.ref, "status": "retired"}
        if operation == "export":
            atomic_write(arguments.out, library.export(arguments.ref))
            return {"path": str(arguments.out), "ref": arguments.ref}
    raise FairyError("invalid", "Unknown operation")


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = _run(arguments)
    except FairyError as exc:
        result = exc.as_dict()
    except sqlite3.Error as exc:
        result = {
            "error": "storage_failed",
            "message": "Storage operation failed; preserve data and inspect state before retrying",
            "sqlite_code": getattr(exc, "sqlite_errorcode", None),
            "sqlite_name": getattr(exc, "sqlite_errorname", None),
        }
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        result = {"error": "operation_failed", "message": type(exc).__name__}
    try:
        encoded = encode_response(arguments.home, result, task=getattr(arguments, "task", None))
    except (FairyError, OSError, sqlite3.Error):
        encoded = (
            canonical(
                {
                    "error": "projection_failed",
                    "message": "Response export failed; work may be recorded. Inspect before retrying.",
                    **controls(result, getattr(arguments, "task", None)),
                }
            )
            + b"\n"
        )
        sys.stdout.buffer.write(encoded)
        return 1
    sys.stdout.buffer.write(encoded)
    if "error" in result:
        return 1
    delivery = result.get("delivery")
    if isinstance(delivery, dict) and delivery.get("state") == "failed":
        return 1
    if result.get("status") in {"failed", "unknown"}:
        return 1
    if result.get("ready") is False:
        return 1
    if "checks" in result and any(
        item["status"] != "ok" or item.get("result", {}).get("verdict") != "pass" for item in result["checks"]
    ):
        return 1
    return 0
