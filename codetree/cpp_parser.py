import re
from typing import Optional, List
from .parser import ParsedFile, ParsedSymbol

# Module detection regexes
MODULE_RE = re.compile(
    r"(?:BOOST_PYTHON_MODULE|PYBIND11_MODULE)\s*\(\s*([a-zA-Z0-9_]+)"
)

# Class extraction regex
# Captures `class_<...>("ClassName"` or `py::class_<...>(m, "ClassName"`
CLASS_RE = re.compile(r'class_\s*<[^"]*>\s*\([^"]*"([^"]+)"')

# Methods, properties, and functions
DEF_RE = re.compile(r'\.def\s*\(\s*"([^"]+)"')
PROP_RE = re.compile(r'\.add_property\s*\(\s*"([^"]+)"')
RWRITE_RE = re.compile(r'\.def_readwrite\s*\(\s*"([^"]+)"')
RONLY_RE = re.compile(r'\.def_readonly\s*\(\s*"([^"]+)"')
STATIC_RE = re.compile(r'\.staticmethod\s*\(\s*"([^"]+)"')

# Free functions at module scope
MDEF_RE = re.compile(r'\bm\.def\s*\(\s*"([^"]+)"')
BPDEF_RE = re.compile(r'^\s*def\s*\(\s*"([^"]+)"')


def parse_cpp_file(abs_path: str, rel_path: str) -> Optional[ParsedFile]:
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    # Step 1: Detect module name
    module_match = MODULE_RE.search(content)
    if not module_match:
        return None

    module_name = module_match.group(1)

    lines = content.splitlines()
    symbols: List[ParsedSymbol] = []

    current_class = None
    paren_depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Helper check to see if a statement ends on this line.
        # We strip trailing comments to be sure (e.g. '.def(...) ; // comment')
        clean_line = stripped.split("//")[0].strip()
        ends_with_semicolon = clean_line.endswith(";")

        # Step 2: Class extraction
        # Look ahead up to 5 lines for a class_<...> declaration
        if "class_<" in line:
            window = " ".join(lines[i : min(i + 5, len(lines))])
            class_match = CLASS_RE.search(window)
            if class_match:
                current_class = class_match.group(1)
                symbols.append(
                    ParsedSymbol(
                        name=current_class,
                        kind="class",
                        signature="()",
                        docstring=None,
                        parent=None,
                        lineno=i + 1,
                        decorators=[],
                    )
                )
                if ends_with_semicolon:
                    current_class = None
                continue

        # Check for properties/methods
        prop_match = (
            PROP_RE.search(line) or RWRITE_RE.search(line) or RONLY_RE.search(line)
        )
        if prop_match:
            symbols.append(
                ParsedSymbol(
                    name=prop_match.group(1),
                    kind="property",
                    signature="",
                    docstring=None,
                    parent=current_class,
                    lineno=i + 1,
                    decorators=[],
                )
            )
            if ends_with_semicolon:
                current_class = None
            continue

        def_match = DEF_RE.search(line) or STATIC_RE.search(line)
        if def_match:
            parent = current_class if current_class else None
            symbols.append(
                ParsedSymbol(
                    name=def_match.group(1),
                    kind="method" if parent else "function",
                    signature="()",
                    docstring=None,
                    parent=parent,
                    lineno=i + 1,
                    decorators=[],
                )
            )
            if ends_with_semicolon:
                current_class = None
            continue

        # Free functions
        free_match = MDEF_RE.search(line) or BPDEF_RE.search(line)
        if free_match:
            symbols.append(
                ParsedSymbol(
                    name=free_match.group(1),
                    kind="function",
                    signature="()",
                    docstring=None,
                    parent=None,
                    lineno=i + 1,
                    decorators=[],
                )
            )
            if ends_with_semicolon:
                current_class = None
            continue

        # Chain break heuristic: if we see a closing semicolon for a statement, we might break the class chain
        if ends_with_semicolon:
            current_class = None

    return ParsedFile(
        path=rel_path,
        module_name=module_name,
        symbols=symbols,
        imports=[],
        docstring=None,
        is_package=False,
    )
