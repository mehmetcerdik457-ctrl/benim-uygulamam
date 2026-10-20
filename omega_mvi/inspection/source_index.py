"""Real, local-only AST index of a fixed set of public OMEGA source files.

Unlike the old synthetic retriever, the entries are derived from source bytes
installed with the demo. No secrets, user directories, GitHub API, subprocess,
network, model, database, or LLM are accessed. This is *structural* analysis,
not a claim that dynamic calls have been fully resolved.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
from pathlib import Path

SOURCE_FILES = (
    "pipeline.py",
    "github_inventory/__init__.py",
    "pr_review/engine.py",
    "redaction/__init__.py",
    "retrieval/__init__.py",
)
MAX_BYTES = 128 * 1024


class SourceIndexError(ValueError):
    pass


def _read_public_file(root: Path, relative: str) -> bytes:
    """Read immutable demo-source files without following directory symlinks."""
    if relative not in SOURCE_FILES:
        raise SourceIndexError("SOURCE_NOT_ALLOWLISTED")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptors = []
    try:
        descriptors.append(os.open(root, directory_flags))
        pieces = relative.split("/")
        for part in pieces[:-1]:
            descriptors.append(os.open(part, directory_flags, dir_fd=descriptors[-1]))
        fd = os.open(pieces[-1], file_flags, dir_fd=descriptors[-1])
        try:
            details = os.fstat(fd)
            if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_BYTES:
                raise SourceIndexError("INVALID_SOURCE_TYPE_OR_SIZE")
            contents = b""
            while len(contents) <= MAX_BYTES:
                chunk = os.read(fd, min(32768, MAX_BYTES + 1 - len(contents)))
                if not chunk:
                    return contents
                contents += chunk
            raise SourceIndexError("SOURCE_TOO_LARGE")
        finally:
            os.close(fd)
    except OSError:
        raise SourceIndexError("SOURCE_UNAVAILABLE") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _expression_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        name = _expression_name(node.value)
        return (name + "." if name else "") + node.attr
    return None


class _Definitions(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[str] = []
        self.symbols: list[dict] = []
        self.imports: set[str] = set()
        self.calls: set[tuple[str, str]] = set()
        self.dynamic_calls = 0

    def _definition(self, node: ast.AST, name: str, kind: str) -> None:
        qualname = ".".join((*self.scope, name))
        self.symbols.append({"symbol": qualname, "kind": kind, "line": node.lineno})
        self.scope.append(name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._definition(node, node.name, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._definition(node, node.name, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._definition(node, node.name, "async_function")

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(x.name for x in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        self.imports.add(module)

    def visit_Call(self, node: ast.Call) -> None:
        callee = _expression_name(node.func)
        if callee:
            caller = ".".join(self.scope) or "<module>"
            self.calls.add((caller, callee))
        else:
            self.dynamic_calls += 1
        self.generic_visit(node)


def index_public_sources(root: Path | None = None) -> dict:
    """Index only explicitly allowlisted *installed public* source modules."""
    if root is None:
        root = Path(__file__).parent
    entries = []
    for relative in SOURCE_FILES:
        raw = _read_public_file(root, relative)
        try:
            code = raw.decode("utf-8", "strict")
            tree = ast.parse(code, filename=relative)
        except (UnicodeDecodeError, SyntaxError):
            raise SourceIndexError("UNPARSEABLE_PUBLIC_SOURCE") from None
        scan = _Definitions()
        scan.visit(tree)
        entries.append({
            "path": "omega_mvi/inspection/" + relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw),
            "symbols": sorted(scan.symbols, key=lambda x: (x["line"], x["symbol"])),
            "imports": sorted(scan.imports),
            "call_edges": [
                {"from": origin, "to": callee}
                for origin, callee in sorted(scan.calls)
            ],
            "dynamic_calls_unresolved": scan.dynamic_calls,
        })
    return {
        "mode": "real-public-source-ast",
        "input": "fixed local installed public modules",
        "files": entries,
        "files_indexed": len(entries),
        "symbol_count": sum(len(x["symbols"]) for x in entries),
        "read_only": True,
        "external_calls": False,
        "authenticated_owner": False,
        "production_ready": False,
        "acceptance": "NOT_ACCEPTED",
    }


if __name__ == "__main__":
    try:
        print(json.dumps(index_public_sources(), sort_keys=True, ensure_ascii=False))
    except SourceIndexError:
        print('{"error":"PUBLIC_SOURCE_INDEX_UNAVAILABLE","acceptance":"NOT_ACCEPTED"}')
        raise SystemExit(1)
