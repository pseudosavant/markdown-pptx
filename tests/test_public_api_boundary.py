"""Keep package generation behind the public pptx API."""

import ast
from pathlib import Path


def test_production_code_uses_only_public_pptx_apis() -> None:
    source_dir = Path(__file__).parents[1] / "src" / "markdown_slides"
    forbidden_modules = ("pptx.oxml", "pptx.opc", "lxml", "xml", "zipfile")
    forbidden_attributes = {
        "_element",
        "_p",
        "_r",
        "_tbl",
        "_tc",
        "_spTree",
        "_sldIdLst",
        "_part",
        "_blob",
        "element",
        "part",
        "rels",
        "xpath",
    }
    violations = []
    for path in source_dir.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            if any(name == prefix or name.startswith(prefix + ".") for name in modules for prefix in forbidden_modules):
                violations.append(f"{path.name}:{node.lineno} imports an XML/package implementation")
            if isinstance(node, ast.Attribute) and node.attr in forbidden_attributes:
                violations.append(f"{path.name}:{node.lineno} accesses {node.attr}")
    assert not violations, "\n".join(violations)
