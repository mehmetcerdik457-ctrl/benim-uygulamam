"""Conservative offline code graph: Python AST plus uncertain JS/TS lexical hints."""
from __future__ import annotations
import ast
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class CodeRelation:
    caller: str
    kind: str
    target: str
    line: int
    confidence: str
    reason: str = ""

def _callee(node):
    if isinstance(node, ast.Name):
        return node.id, False
    if isinstance(node, ast.Attribute):
        base, _ = _callee(node.value)
        return base + "." + node.attr, True
    return "<dynamic>", True

class _PythonGraph(ast.NodeVisitor):
    def __init__(self):
        self.result = []
        self.context = []

    def _fn(self, node):
        qualified = ".".join((*self.context, node.name))
        self.result.append(CodeRelation(qualified, "definition", qualified, node.lineno, "parsed"))
        self.context.append(node.name)
        self.generic_visit(node)
        self.context.pop()

    visit_FunctionDef = _fn
    visit_AsyncFunctionDef = _fn

    def visit_ClassDef(self, node):
        self.context.append(node.name)
        self.generic_visit(node)
        self.context.pop()

    def visit_Lambda(self, node):
        self.result.append(CodeRelation(".".join(self.context) or "<module>",
                          "callback", "<lambda>", node.lineno, "parsed",
                          "Callback target cannot be inferred"))
        self.generic_visit(node)

    def visit_Import(self, node):
        for item in node.names:
            self.result.append(CodeRelation(".".join(self.context) or "<module>",
                               "import", item.name, node.lineno, "parsed"))

    def visit_ImportFrom(self, node):
        for item in node.names:
            self.result.append(CodeRelation(".".join(self.context) or "<module>",
                               "import", "." * node.level + (node.module or "") +
                               "." + item.name, node.lineno, "parsed"))

    def visit_Call(self, node):
        callee, uncertain = _callee(node.func)
        uncertain = uncertain or callee in {"getattr", "setattr", "eval", "exec", "__import__"}
        self.result.append(CodeRelation(".".join(self.context) or "<module>",
                           "call", callee, node.lineno, "unknown" if uncertain else "syntax_only",
                           "Dynamic dispatch unresolved" if uncertain else "Name binding not resolved"))
        for arg in (*node.args, *(keyword.value for keyword in node.keywords)):
            if isinstance(arg, ast.Name):
                self.result.append(CodeRelation(".".join(self.context) or "<module>",
                                   "callback_candidate", arg.id, node.lineno,
                                   "unknown", "Argument may or may not be callable"))
        self.generic_visit(node)

def _scrub_js(code):
    # NOT a parser: strings, regexes, templates, JSX and TS typing are approximate.
    pattern = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|\"(?:\\.|[^\"\\])*\"|\'(?:\\.|[^\'\\])*\'')
    return pattern.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), code)

def analyze_source(language: str, code: str) -> tuple[CodeRelation, ...]:
    if language not in {"python", "javascript", "typescript"}:
        raise ValueError("UNSUPPORTED_LANGUAGE")
    if type(code) is not str or len(code) > 200_000:
        raise ValueError("INVALID_SOURCE")
    if language == "python":
        visitor = _PythonGraph()
        visitor.visit(ast.parse(code))
        return tuple(visitor.result)
    src = _scrub_js(code)
    results = []
    def add(kind, target, pos):
        results.append(CodeRelation("<scope_unknown>", kind, target, src.count("\n", 0, pos) + 1,
                                    "unknown" if kind == "dynamic_call" else "heuristic",
                                    "JS/TS lexer only; binding/dynamic dispatch unresolved"))
    for match in re.finditer(r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", src):
        add("definition", match.group(1), match.start())
    for match in re.finditer(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w$]+)\s*=>", src):
        add("callback_or_arrow_definition", match.group(1), match.start())
    for match in re.finditer(r"\bimport\s+", src):
        add("import_candidate", "<module_unresolved>", match.start())
    ignored = {"if", "for", "while", "switch", "catch", "function", "typeof", "return", "new"}
    for match in re.finditer(r"(?<![\w$])([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(", src):
        name = match.group(1)
        before = src[max(0, match.start()-16):match.start()]
        if name in ignored or re.search(r"\b(?:function|class|new)\s+$", before):
            continue
        add("call_candidate", name, match.start())
    for match in re.finditer(r"\b(?:eval|Function)\s*\(|(?:[\w$]+\s*)\[.*?\]\s*\(", src):
        add("dynamic_call", "<dynamic>", match.start())
    for match in re.finditer(r"\b(?:addEventListener|setTimeout|then|map|filter)\s*\(\s*(?:\([^)]*\)|[\w$]+)\s*=>", src):
        add("callback_candidate", "<inline_arrow>", match.start())
    return tuple(sorted(results, key=lambda x: (x.line, x.kind, x.target)))
