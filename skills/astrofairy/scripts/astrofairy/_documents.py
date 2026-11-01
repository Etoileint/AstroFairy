from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NoReturn, Self, cast

from astrofairy._contracts import canonical, dependency_issues, digest, parse_json
from astrofairy._errors import FairyError

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from types import TracebackType

MAX_NODE_BYTES = 16 * 1024
CHUNK_CHARACTERS = 2048
FANOUT = 16
CACHE_NODES = 128
KEY_PREFIX = 16
_NAMESPACE = b"AstroFairy document node 1\0"
_REF = re.compile(r"[a-f0-9]{64}\Z")
_TASK = re.compile(r"[a-f0-9]{32}\Z")
_VALUE_KINDS = {"scalar", "array", "object"}


def _invalid() -> NoReturn:
    raise FairyError("integrity", "Invalid authenticated document block")


def _require(condition: bool) -> None:  # noqa: FBT001 - asserts a predicate, not a behavior switch.
    if not condition:
        _invalid()


def _owner(task: str | None) -> None:
    if task is not None and (not isinstance(task, str) or not _TASK.fullmatch(task)):
        raise FairyError("invalid", "Invalid document owner")


@dataclass(frozen=True)
class _Edge:
    ref: str
    characters: int
    size: int
    role: str
    count: int | None = None

    def encoded(self) -> list[Any]:
        return (
            [self.ref, self.characters, self.size]
            if self.count is None
            else [self.ref, self.count, self.characters, self.size]
        )


def _edge(value: Any, role: str) -> _Edge:
    indexed = role in {"items", "members"}
    _require(isinstance(value, list) and len(value) == (4 if indexed else 3))
    _require(isinstance(value[0], str) and bool(_REF.fullmatch(value[0])))
    _require(all(type(item) is int and item >= 0 for item in value[1:]))
    _require(value[-1] >= value[-2] and (indexed or value[-2] > 0))
    return _Edge(value[0], value[-2], value[-1], role, value[1] if indexed else None)


class _Node:
    def __init__(self, archive: _Archive, ref: str, body: dict[str, Any]) -> None:
        self.archive, self.ref, self.body = archive, ref, body
        self.kind = body.get("kind")
        self.parts: list[str | _Edge] = []
        self.count: int | None = None
        kind = self.kind
        if kind == "text":
            _require(set(body) == {"kind", "text"} and isinstance(body["text"], str))
            _require(0 < len(body["text"]) <= CHUNK_CHARACTERS)
            self.parts = [body["text"]]
        elif kind == "concat":
            _require(set(body) == {"kind", "children"})
            self.parts = list(self._children(body["children"], "span"))
        elif kind == "scalar":
            _require(set(body) == {"kind", "json_type", "text"})
            _require(body["json_type"] in {"string", "integer", "float", "boolean", "null"})
            self.parts = [_edge(body["text"], "span")]
        elif kind in {"array", "object"}:
            _require(set(body) == {"kind", "index"})
            edge = _edge(body["index"], "items" if kind == "array" else "members")
            self.count = edge.count
            self.parts = ["[" if kind == "array" else "{", edge, "]" if kind == "array" else "}"]
        elif kind == "items":
            _require(set(body) == {"kind", "entries"})
            self._entries(body["entries"])
            self.count = len(body["entries"])
            self.parts = self._joined([_edge(item, "value") for item in body["entries"]])
        elif kind == "members":
            _require(set(body) == {"kind", "entries"})
            self._entries(body["entries"])
            self.count = len(body["entries"])
            for index, item in enumerate(body["entries"]):
                _require(isinstance(item, list) and len(item) == 4)
                _require(isinstance(item[0], str) and type(item[1]) is int and item[1] >= 0)
                _require(len(item[0]) == min(item[1], KEY_PREFIX))
                if index:
                    self.parts.append(",")
                self.parts.extend([_edge(item[2], "key"), ":", _edge(item[3], "value")])
        elif kind == "index":
            _require(set(body) == {"kind", "layout", "children"})
            _require(body["layout"] in {"items", "members"})
            children = self._children(body["children"], body["layout"])
            _require(all(item.count is not None and item.count > 0 for item in children))
            self.count = sum(item.count or 0 for item in children)
            self.parts = self._joined(children)
        elif kind == "document":
            _require(set(body) == {"kind", "format", "owner", "value"})
            _require(type(body["format"]) is int and body["format"] == 1)
            _require(
                body["owner"] is None
                or (isinstance(body["owner"], str) and bool(_TASK.fullmatch(body["owner"])))
            )
            self.parts = [_edge(body["value"], "value")]
        else:
            _invalid()
        self.characters = sum(len(item) if isinstance(item, str) else item.characters for item in self.parts)
        self.size = sum(
            len(item.encode("utf-8")) if isinstance(item, str) else item.size for item in self.parts
        )

    @staticmethod
    def _entries(value: Any) -> None:
        _require(isinstance(value, list) and len(value) <= FANOUT)

    @classmethod
    def _children(cls, value: Any, role: str) -> list[_Edge]:
        cls._entries(value)
        _require(bool(value))
        return [_edge(item, role) for item in value]

    @staticmethod
    def _joined(edges: list[_Edge]) -> list[str | _Edge]:
        parts: list[str | _Edge] = []
        for index, edge in enumerate(edges):
            if index:
                parts.append(",")
            parts.append(edge)
        return parts

    def edge(self, role: str) -> _Edge:
        return _Edge(
            self.ref, self.characters, self.size, role, self.count if role in {"items", "members"} else None
        )

    def __repr__(self) -> str:
        return "<authenticated document node>"


def _version(connection: sqlite3.Connection) -> None:
    try:
        columns = connection.execute("PRAGMA table_info(metadata)").fetchall()
        nodes = connection.execute("PRAGMA table_info(nodes)").fetchall()
        _require([(x[1], x[2], x[3], x[5]) for x in columns] == [("version", "INTEGER", 1, 0)])
        _require(
            [(x[1], x[2], x[3], x[5]) for x in nodes] == [("ref", "TEXT", 1, 1), ("payload", "BLOB", 1, 0)]
        )
        rows = connection.execute("SELECT version, typeof(version) FROM metadata").fetchall()
        _require(rows == [(1, "integer")])
    except (FairyError, sqlite3.DatabaseError) as exc:
        raise FairyError("version", "Unsupported document archive; use a fresh home") from exc


@contextmanager
def _schema_admission(path: Path) -> Iterator[None]:
    try:
        from filelock import FileLock, Timeout  # noqa: PLC0415 - readiness must work before runtime imports.
    except Exception as exc:
        raise FairyError("runtime_setup_required", "Prepare the locked native file lock dependency") from exc
    try:
        with FileLock(
            str(path) + ".init.lock",
            timeout=10,
            mode=0o600,
            fallback_to_soft=False,
            preserve_lock_file=True,
        ):
            yield
    except (FairyError, sqlite3.Error):
        raise
    except Timeout as exc:
        raise FairyError("storage_busy", "Document initialization is busy; inspect before retrying") from exc
    except Exception as exc:
        raise FairyError(
            "runtime_setup_required", "Document initialization requires working native locks and storage"
        ) from exc


def _writer(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    connection = None
    try:
        with _schema_admission(path):
            fresh = False
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
                fresh = True
            connection = sqlite3.connect(
                path.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=10
            )
            if fresh:
                connection.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE metadata(version INTEGER NOT NULL);
                    INSERT INTO metadata VALUES (1);
                    CREATE TABLE nodes(ref TEXT PRIMARY KEY NOT NULL, payload BLOB NOT NULL);
                    COMMIT;
                """)
            _version(connection)
            path.chmod(0o600)
        if connection is None:
            _invalid()
        return connection
    except BaseException:
        if connection is not None:
            connection.close()
        raise


class _Archive:
    def __init__(self, home: Path, *, write: bool = False) -> None:
        issues = dependency_issues()
        if issues:
            raise FairyError(
                "runtime_setup_required",
                "Prepare the locked runtime dependencies",
                details={"dependencies": issues},
            )
        path = home.resolve() / "documents.sqlite3"
        self.write = write
        self.cache: OrderedDict[str, _Node] = OrderedDict()
        if write:
            self.connection = _writer(path)
        else:
            if not path.is_file():
                raise FairyError("missing", "Unknown document archive")
            self.connection = sqlite3.connect(
                path.as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=10
            )
        try:
            if write:
                self.connection.execute("BEGIN IMMEDIATE")
            else:
                _version(self.connection)
        except BaseException:
            self.connection.close()
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, _exc: BaseException | None, _trace: TracebackType | None
    ) -> None:
        try:
            if self.write and self.connection.in_transaction:
                self.connection.execute("COMMIT" if exc_type is None else "ROLLBACK")
        finally:
            self.cache.clear()
            self.connection.close()

    def fetch(self, ref: str) -> bytes | None:
        row = self.connection.execute(
            "SELECT length(payload), typeof(payload), substr(payload, 1, ?) FROM nodes WHERE ref = ?",
            (MAX_NODE_BYTES + 1, ref),
        ).fetchone()
        if row is None:
            return None
        _require(row[1] == "blob" and row[0] <= MAX_NODE_BYTES)
        return bytes(row[2])

    def _remember(self, node: _Node) -> _Node:
        self.cache[node.ref] = node
        self.cache.move_to_end(node.ref)
        while len(self.cache) > CACHE_NODES:
            self.cache.popitem(last=False)
        return node

    def get(self, ref: str) -> _Node:
        _require(isinstance(ref, str) and bool(_REF.fullmatch(ref)))
        if ref in self.cache:
            self.cache.move_to_end(ref)
            return self.cache[ref]
        data = self.fetch(ref)
        if data is None:
            raise FairyError("integrity", "Missing authenticated document block")
        _require(digest(_NAMESPACE + data) == ref)
        try:
            body = parse_json(data.decode("utf-8"))
            _require(isinstance(body, dict) and canonical(body) == data)
            return self._remember(_Node(self, ref, body))
        except (FairyError, UnicodeError, TypeError, KeyError) as exc:
            raise FairyError("integrity", "Invalid authenticated document block") from exc

    def expect(self, edge: _Edge) -> _Node:
        node = self.get(edge.ref)
        _require((node.characters, node.size) == (edge.characters, edge.size))
        if edge.role in {"items", "members"}:
            _require(node.kind == edge.role or (node.kind == "index" and node.body["layout"] == edge.role))
            _require(node.count == edge.count)
        elif edge.role == "span":
            _require(node.kind in {"text", "concat"})
        elif edge.role == "key":
            _require(node.kind == "scalar" and node.body["json_type"] == "string")
        else:
            _require(edge.role == "value" and node.kind in _VALUE_KINDS)
        return node

    def put(self, body: dict[str, Any]) -> _Node:
        data = canonical(body)
        if len(data) > MAX_NODE_BYTES:
            raise FairyError("limit", "Document block exceeds its layout budget")
        ref = digest(_NAMESPACE + data)
        node = _Node(self, ref, body)
        existing = self.fetch(ref)
        if existing is None:
            self.connection.execute("INSERT INTO nodes VALUES (?, ?)", (ref, data))
        else:
            _require(existing == data)
        return self._remember(node)

    def span(self, text: str) -> _Node:
        nodes = [
            self.put({"kind": "text", "text": text[start : start + CHUNK_CHARACTERS]})
            for start in range(0, len(text), CHUNK_CHARACTERS)
        ]
        while len(nodes) > 1:
            nodes = [
                self.put(
                    {
                        "kind": "concat",
                        "children": [item.edge("span").encoded() for item in nodes[start : start + FANOUT]],
                    }
                )
                for start in range(0, len(nodes), FANOUT)
            ]
        return nodes[0]

    def index(self, layout: str, entries: list[Any]) -> _Node:
        nodes = [
            self.put({"kind": layout, "entries": entries[start : start + FANOUT]})
            for start in range(0, len(entries), FANOUT)
        ]
        if not nodes:
            nodes = [self.put({"kind": layout, "entries": []})]
        while len(nodes) > 1:
            nodes = [
                self.put(
                    {
                        "kind": "index",
                        "layout": layout,
                        "children": [item.edge(layout).encoded() for item in nodes[start : start + FANOUT]],
                    }
                )
                for start in range(0, len(nodes), FANOUT)
            ]
        return nodes[0]

    def build(self, value: Any) -> _Node:
        stack: list[tuple[str, Any]] = [("value", value)]
        built: list[_Node] = []
        while stack:
            mode, item = stack.pop()
            if mode == "value" and isinstance(item, dict):
                keys = sorted(item)
                stack.append(("object", keys))
                for key in reversed(keys):
                    stack.extend([("value", item[key]), ("value", key)])
            elif mode == "value" and isinstance(item, list):
                stack.append(("array", len(item)))
                stack.extend(("value", child) for child in reversed(item))
            elif mode == "value":
                kind = {str: "string", int: "integer", float: "float", bool: "boolean", type(None): "null"}[
                    type(item)
                ]
                built.append(
                    self.put(
                        {
                            "kind": "scalar",
                            "json_type": kind,
                            "text": self.span(canonical(item).decode("utf-8")).edge("span").encoded(),
                        }
                    )
                )
            else:
                count = item if mode == "array" else 2 * len(item)
                children = built[-count:] if count else []
                if count:
                    del built[-count:]
                entries = (
                    [child.edge("value").encoded() for child in children]
                    if mode == "array"
                    else [
                        [
                            key[:KEY_PREFIX],
                            len(key),
                            children[2 * n].edge("key").encoded(),
                            children[2 * n + 1].edge("value").encoded(),
                        ]
                        for n, key in enumerate(item)
                    ]
                )
                indexed = self.index("items" if mode == "array" else "members", entries)
                built.append(
                    self.put(
                        {
                            "kind": mode,
                            "index": indexed.edge("items" if mode == "array" else "members").encoded(),
                        }
                    )
                )
        _require(len(built) == 1)
        return built[0]

    def fragment(self, node: _Node, offset: int, limit: int) -> str:
        _require(0 <= offset <= node.characters and limit >= 0)
        limit = min(limit, node.characters - offset)
        stack: list[str | _Edge] = [node.edge("value") if node.kind in _VALUE_KINDS else node.edge("span")]
        result: list[str] = []
        while stack and limit:
            part = stack.pop()
            length = len(part) if isinstance(part, str) else part.characters
            if offset >= length:
                offset -= length
            elif isinstance(part, str):
                text = part[offset : offset + limit]
                result.append(text)
                limit -= len(text)
                offset = 0
            else:
                stack.extend(reversed(self.expect(part).parts))
        _require(limit == 0)
        return "".join(result)

    def entry(self, edge: _Edge, index: int) -> Any:
        if index < 0 or edge.count is None or index >= edge.count:
            raise IndexError
        node = self.expect(edge)
        while node.kind == "index":
            for encoded in node.body["children"]:
                child = _edge(encoded, node.body["layout"])
                if index < (child.count or 0):
                    node = self.expect(child)
                    break
                index -= child.count or 0
            else:
                _invalid()
        return node.body["entries"][index]

    def key(self, entry: list[Any]) -> str:
        node = self.expect(_edge(entry[2], "key"))
        value = parse_json(self.fragment(node, 0, node.characters))
        _require(isinstance(value, str) and value[:KEY_PREFIX] == entry[0] and len(value) == entry[1])
        return cast("str", value)

    def member(self, node: _Node, key: str) -> _Node:
        edge = _edge(node.body["index"], "members")
        low, high = 0, edge.count or 0
        while low < high:
            middle = (low + high) // 2
            entry = self.entry(edge, middle)
            prefix = key[:KEY_PREFIX]
            if prefix != entry[0]:
                comparison = (prefix > entry[0]) - (prefix < entry[0])
            elif len(key) <= KEY_PREFIX and entry[1] > KEY_PREFIX:
                comparison = -1
            else:
                actual = entry[0] if entry[1] <= KEY_PREFIX else self.key(entry)
                comparison = (key > actual) - (key < actual)
            if comparison == 0:
                _require(self.key(entry) == key)
                return self.expect(_edge(entry[3], "value"))
            if comparison < 0:
                high = middle
            else:
                low = middle + 1
        raise KeyError(key)


class _Value:
    def __init__(self, node: _Node) -> None:
        self.node = node

    def __repr__(self) -> str:
        return "<authenticated JSON value>"


class _Object(_Value, Mapping[str, _Value]):
    def __getitem__(self, key: str) -> _Value:
        return _view(self.node.archive.member(self.node, key))

    def __iter__(self) -> Iterator[str]:
        edge = _edge(self.node.body["index"], "members")
        for index in range(edge.count or 0):
            yield self.node.archive.key(self.node.archive.entry(edge, index))

    def __len__(self) -> int:
        return self.node.count or 0


class _Array(_Value, Sequence[_Value]):
    def __getitem__(self, index: Any) -> Any:
        if type(index) is not int:
            raise IndexError
        edge = _edge(self.node.body["index"], "items")
        return _view(self.node.archive.expect(_edge(self.node.archive.entry(edge, index), "value")))

    def __len__(self) -> int:
        return self.node.count or 0


def _view(node: _Node) -> _Value:
    return _Object(node) if node.kind == "object" else _Array(node) if node.kind == "array" else _Value(node)


def _root(archive: _Archive, ref: str, task: str | None) -> _Node:
    _owner(task)
    if not isinstance(ref, str) or not _REF.fullmatch(ref):
        raise FairyError("invalid", "Invalid document reference")
    if archive.fetch(ref) is None:
        raise FairyError("missing", "Unknown document reference")
    root = archive.get(ref)
    _require(root.kind == "document")
    if root.body["owner"] != task:
        raise FairyError("permission", "Document does not belong to this task scope")
    return archive.expect(_edge(root.body["value"], "value"))


def _metadata(ref: str, task: str | None, node: _Node) -> dict[str, Any]:
    result: dict[str, Any] = {"document": ref, "task": task, "bytes": node.size}
    if node.kind == "object":
        try:
            sequence = node.archive.member(node, "seq")
        except KeyError:
            pass
        else:
            if sequence.kind == "scalar" and sequence.body["json_type"] == "integer":
                result["seq"] = parse_json(sequence.archive.fragment(sequence, 0, sequence.characters))
    return result


def freeze(home: Path, value: Any, *, task: str | None = None) -> dict[str, Any]:
    _owner(task)
    normalized = parse_json(canonical(value).decode("utf-8"))
    with _Archive(home, write=True) as archive:
        node = archive.build(normalized)
        root = archive.put(
            {"kind": "document", "format": 1, "owner": task, "value": node.edge("value").encoded()}
        )
        return _metadata(root.ref, task, node)


@contextmanager
def select(
    home: Path, ref: str, *, task: str | None = None, pointer: str = ""
) -> Iterator[tuple[_Node, dict[str, Any]]]:
    with _Archive(home) as archive:
        node = _root(archive, ref, task)
        metadata = _metadata(ref, task, node)
        try:
            from jsonpointer import JsonPointerException, resolve_pointer  # type: ignore[import-untyped]  # noqa: PLC0415
        except Exception as exc:
            raise FairyError("runtime_setup_required", "Prepare the locked JSON Pointer dependency") from exc
        try:
            selected = resolve_pointer(_view(node), pointer)
        except (JsonPointerException, TypeError, ValueError) as exc:
            raise FairyError("invalid", "JSON Pointer does not select an existing JSON value") from exc
        if not isinstance(selected, _Value):
            raise FairyError("invalid", "JSON Pointer does not select an existing JSON value")
        yield (
            selected.node,
            {
                **metadata,
                "selection": selected.node.ref,
                "characters": selected.node.characters,
                "integrity": "selected",
            },
        )


def _audit_nodes(archive: _Archive, nodes: Iterable[_Node], seen: set[str]) -> int:
    roots = 0
    for node in nodes:
        pending = [node]
        while pending:
            current = pending.pop()
            if current.ref in seen:
                continue
            seen.add(current.ref)
            roots += current.kind == "document"
            if current.kind == "scalar":
                text = archive.fragment(current, 0, current.characters)
                value = parse_json(text)
                kind = {
                    str: "string",
                    int: "integer",
                    float: "float",
                    bool: "boolean",
                    type(None): "null",
                }.get(type(value))
                _require(kind == current.body["json_type"] and canonical(value).decode("utf-8") == text)
            elif current.kind == "object":
                edge = _edge(current.body["index"], "members")
                previous: str | None = None
                for index in range(edge.count or 0):
                    key = archive.key(archive.entry(edge, index))
                    _require(previous is None or previous < key)
                    previous = key
            pending.extend(archive.expect(part) for part in current.parts if isinstance(part, _Edge))
    return roots


def audit_archive(home: Path) -> dict[str, int]:
    with _Archive(home) as archive:
        _require(archive.connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
        seen: set[str] = set()
        nodes = (
            archive.get(row[0])
            for row in archive.connection.execute("SELECT ref FROM nodes")
            if row[0] not in seen
        )
        roots = _audit_nodes(archive, nodes, seen)
        return {"document_nodes": len(seen), "documents": roots}


def audit_document(home: Path, ref: str, *, task: str | None = None) -> dict[str, Any]:
    with _Archive(home) as archive:
        node = _root(archive, ref, task)
        seen = {ref}
        _audit_nodes(archive, [node], seen)
        checksum = hashlib.sha256()
        offset = 0
        while offset < node.characters:
            text = archive.fragment(node, offset, min(8192, node.characters - offset))
            _require(bool(text))
            checksum.update(text.encode("utf-8"))
            offset += len(text)
        return {
            **_metadata(ref, task, node),
            "selection": node.ref,
            "integrity": "full",
            "verified_nodes": len(seen),
            "canonical_sha256": checksum.hexdigest(),
        }
