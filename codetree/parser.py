import ast
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ParsedSymbol:
    name: str
    kind: str  # "class" | "function" | "method" | "async_function"
    lineno: int
    signature: str  # Reconstructed from ast.arguments (includes type hints)
    docstring: Optional[str]
    decorators: List[str]
    parent: Optional[str]  # For methods: the enclosing class name


@dataclass
class ImportEntry:
    module: Optional[str]  # e.g. "os.path", "mypackage.utils"
    names: List[str]  # Specific names imported; empty list means "import module"
    alias: Optional[str]
    is_relative: bool
    level: int  # Number of leading dots for relative imports


@dataclass
class ParsedFile:
    path: str  # Root-relative path
    module_name: str  # Dotted module name derived from path
    symbols: List[ParsedSymbol]
    imports: List[ImportEntry]
    docstring: Optional[str]
    is_package: bool = False


def _get_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        sig = f"({ast.unparse(node.args)})"
    except Exception:
        sig = "()"

    if node.returns:
        try:
            sig += f" -> {ast.unparse(node.returns)}"
        except Exception:
            pass

    return sig


class CodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.symbols: List[ParsedSymbol] = []
        self.imports: List[ImportEntry] = []
        self.current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(
                ImportEntry(
                    module=alias.name,
                    names=[],
                    alias=alias.asname,
                    is_relative=False,
                    level=0,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.imports.append(
            ImportEntry(
                module=node.module,
                names=[alias.name for alias in node.names],
                alias=None,
                is_relative=node.level > 0,
                level=node.level,
            )
        )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Support cctbx's bp.import_ext("module_name") or import_ext("module_name")
        is_import_ext = False
        if isinstance(node.func, ast.Attribute) and node.func.attr == "import_ext":
            is_import_ext = True
        elif isinstance(node.func, ast.Name) and node.func.id == "import_ext":
            is_import_ext = True

        if (
            is_import_ext
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            module_name = node.args[0].value
            self.imports.append(
                ImportEntry(
                    module=module_name, names=[], alias=None, is_relative=False, level=0
                )
            )
        self.generic_visit(node)

    def _get_decorators(self, node) -> List[str]:
        decs = []
        for d in node.decorator_list:
            try:
                decs.append(ast.unparse(d))
            except Exception:
                pass
        return decs

    def visit_Assign(self, node: ast.Assign):
        # Only parse module-level constants (not inside class or function)
        if self.current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # We capture __all__ as well as uppercase constants
                    if name == "__all__" or (name.isupper() and name.isidentifier()):
                        try:
                            val_str = ast.unparse(node.value)
                        except Exception:
                            val_str = ""
                        self.symbols.append(
                            ParsedSymbol(
                                name=name,
                                kind="constant",
                                lineno=node.lineno,
                                signature=f" = {val_str}",
                                docstring=None,
                                decorators=[],
                                parent=None,
                            )
                        )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if self.current_class is None and isinstance(node.target, ast.Name):
            name = node.target.id
            is_type_alias = False
            # Check if type annotated as TypeAlias
            if (
                isinstance(node.annotation, ast.Name)
                and node.annotation.id == "TypeAlias"
            ):
                is_type_alias = True
            elif (
                isinstance(node.annotation, ast.Attribute)
                and node.annotation.attr == "TypeAlias"
            ):
                is_type_alias = True

            if is_type_alias or (name.isupper() and name.isidentifier()):
                try:
                    val_str = f" = {ast.unparse(node.value)}" if node.value else ""
                except Exception:
                    val_str = ""
                try:
                    ann_str = f": {ast.unparse(node.annotation)}"
                except Exception:
                    ann_str = ""
                self.symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind="type_alias" if is_type_alias else "constant",
                        lineno=node.lineno,
                        signature=f"{ann_str}{val_str}",
                        docstring=None,
                        decorators=[],
                        parent=None,
                    )
                )
        self.generic_visit(node)

    def visit_TypeAlias(self, node: ast.TypeAlias):
        if self.current_class is None and isinstance(node.name, ast.Name):
            name = node.name.id
            try:
                val_str = ast.unparse(node.value)
            except Exception:
                val_str = ""
            self.symbols.append(
                ParsedSymbol(
                    name=name,
                    kind="type_alias",
                    lineno=node.lineno,
                    signature=f" = {val_str}",
                    docstring=None,
                    decorators=[],
                    parent=None,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.symbols.append(
            ParsedSymbol(
                name=node.name,
                kind="class",
                lineno=node.lineno,
                signature=f"({', '.join(ast.unparse(b) for b in node.bases)})"
                if node.bases
                else "()",
                docstring=ast.get_docstring(node),
                decorators=self._get_decorators(node),
                parent=None,
            )
        )

        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.symbols.append(
            ParsedSymbol(
                name=node.name,
                kind="method" if self.current_class else "function",
                lineno=node.lineno,
                signature=_get_signature(node),
                docstring=ast.get_docstring(node),
                decorators=self._get_decorators(node),
                parent=self.current_class,
            )
        )
        # Do not visit body to avoid nested functions/classes cluttering the map.

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.symbols.append(
            ParsedSymbol(
                name=node.name,
                kind="async_method" if self.current_class else "async_function",
                lineno=node.lineno,
                signature=_get_signature(node),
                docstring=ast.get_docstring(node),
                decorators=self._get_decorators(node),
                parent=self.current_class,
            )
        )
        # Do not visit body to avoid nested functions/classes cluttering the map.


def parse_file(abs_path: str, rel_path: str) -> Optional[ParsedFile]:
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError:
        return None

    try:
        tree = ast.parse(source, filename=abs_path)
    except SyntaxError:
        return None

    docstring = ast.get_docstring(tree)

    visitor = CodeVisitor()
    visitor.visit(tree)

    # Derive module name from relative path
    # e.g. "codetree/parser.py" -> "codetree.parser"
    # "codetree/__init__.py" -> "codetree"
    parts = list(Path(rel_path).with_suffix("").parts)
    is_package = False
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
        is_package = True
    module_name = ".".join(parts) if parts else ""

    return ParsedFile(
        path=rel_path,
        module_name=module_name,
        symbols=visitor.symbols,
        imports=visitor.imports,
        docstring=docstring,
        is_package=is_package,
    )
