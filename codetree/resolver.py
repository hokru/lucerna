import sys
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from .parser import ParsedFile, ImportEntry

try:
    STDLIB_MODULES = sys.stdlib_module_names  # Python 3.10+
except AttributeError:
    # Hardcoded fallback for Python 3.9
    STDLIB_MODULES = frozenset(sys.builtin_module_names) | frozenset({
        "abc", "ast", "asyncio", "base64", "collections", "concurrent",
        "configparser", "contextlib", "copy", "csv", "dataclasses", "datetime",
        "decimal", "email", "enum", "fnmatch", "fractions", "functools",
        "glob", "gzip", "hashlib", "heapq", "hmac", "html", "http",
        "importlib", "inspect", "io", "itertools", "json", "keyword",
        "linecache", "logging", "math", "multiprocessing", "operator",
        "os", "pathlib", "pickle", "platform", "pprint", "queue",
        "random", "re", "shutil", "signal", "socket", "sqlite3",
        "ssl", "stat", "statistics", "string", "struct", "subprocess",
        "sys", "tempfile", "textwrap", "threading", "time", "timeit",
        "tkinter", "traceback", "typing", "unittest", "urllib", "uuid",
        "warnings", "weakref", "xml", "xmlrpc", "zipfile", "zipimport",
    })

@dataclass
class ResolvedImport:
    entry: ImportEntry
    status: str             # "internal" | "stdlib" | "external" | "unresolvable"
    target_module: Optional[str]   # if internal, the resolved dotted module name

def _resolve_relative(module_name: str, import_level: int, import_module: Optional[str], is_package: bool = False) -> Optional[str]:
    """Resolve a relative import to an absolute module name."""
    if not module_name:
        parts = []
    else:
        parts = module_name.split('.')
        
    # If this is a package (__init__.py), its module name represents the directory itself.
    # Therefore, a relative import level of 1 means importing from the package directory itself,
    # so we shouldn't strip the last module component (which represents the directory).
    # Decrement the level of traversal by 1 to compensate.
    effective_level = import_level
    if is_package and effective_level > 0:
        effective_level -= 1
        
    # Go up levels
    if effective_level > len(parts):
        # Trying to go above top-level package
        return None
        
    if effective_level > 0:
        parts = parts[:-effective_level]
        
    if import_module:
        parts.extend(import_module.split('.'))
        
    return '.'.join(parts)

def resolve_imports(parsed_files: List[ParsedFile]) -> Dict[str, List[ResolvedImport]]:
    """
    Resolves imports for all files.
    Returns: Dict mapping file module_name -> list of ResolvedImport
    """
    internal_modules: Set[str] = {pf.module_name for pf in parsed_files}
    
    # We also need to recognize packages as internal modules.
    # If "a.b" is a module, "a" is also a module.
    package_modules: Set[str] = set()
    for m in internal_modules:
        parts = m.split('.')
        for i in range(1, len(parts)):
            package_modules.add('.'.join(parts[:i]))
            
    all_internal = internal_modules | package_modules

    resolved_map: Dict[str, List[ResolvedImport]] = {}

    for pf in parsed_files:
        resolved_list = []
        
        for imp in pf.imports:
            # Determine the absolute module name requested
            if imp.is_relative:
                # Need to check if pf has is_package attribute (parsed C++ files don't have it unless handled)
                is_pkg = getattr(pf, 'is_package', False)
                target = _resolve_relative(pf.module_name, imp.level, imp.module, is_package=is_pkg)
            else:
                target = imp.module
                
            if not target:
                resolved_list.append(ResolvedImport(imp, "unresolvable", None))
                continue

            # Check if internal
            if target in all_internal:
                resolved_list.append(ResolvedImport(imp, "internal", target))
            else:
                # Get root module name to check stdlib
                root_module = target.split('.')[0]
                if root_module in STDLIB_MODULES:
                    # External but stdlib
                    resolved_list.append(ResolvedImport(imp, "stdlib", target))
                else:
                    # External third-party
                    resolved_list.append(ResolvedImport(imp, "external", target))

        resolved_map[pf.module_name] = resolved_list

    return resolved_map
