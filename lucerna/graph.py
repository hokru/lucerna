from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from .parser import ParsedFile, ParsedSymbol
from .resolver import ResolvedImport


@dataclass
class FileNode:
    path: str
    module_name: str
    symbols: List[ParsedSymbol]
    docstring: Optional[str]
    external_imports: List[str]  # Third-party pip package names (display only)
    stdlib_imports: List[str]  # Stdlib module names (display only)


@dataclass
class ImportEdge:
    source: str  # Module name of the importer
    target: str  # Module name of the importee (internal files only)
    imported_names: List[str]


class CodeGraph:
    def __init__(self):
        self.nodes: Dict[str, FileNode] = {}
        self.edges: List[ImportEdge] = []

        # Caches for quick traversal
        self._successors: Dict[str, Set[str]] = {}
        self._predecessors: Dict[str, Set[str]] = {}

    def add_node(self, node: FileNode):
        self.nodes[node.module_name] = node
        self._successors.setdefault(node.module_name, set())
        self._predecessors.setdefault(node.module_name, set())

    def add_edge(self, edge: ImportEdge):
        self.edges.append(edge)
        self._successors.setdefault(edge.source, set()).add(edge.target)
        self._predecessors.setdefault(edge.target, set()).add(edge.source)

    def successors(self, module_name: str) -> List[str]:
        """Modules this file imports."""
        return list(self._successors.get(module_name, set()))

    def predecessors(self, module_name: str) -> List[str]:
        """Modules that import this file."""
        return list(self._predecessors.get(module_name, set()))

    def neighborhood(self, module_name: str, depth: int = 1) -> "CodeGraph":
        subgraph = CodeGraph()
        if module_name not in self.nodes:
            return subgraph

        from collections import deque

        visited = set()
        queue = deque([(module_name, 0)])

        while queue:
            curr, d = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)

            subgraph.add_node(self.nodes[curr])

            if d < depth:
                for nxt in self.successors(curr):
                    if nxt in self.nodes and nxt not in visited:
                        queue.append((nxt, d + 1))
                for nxt in self.predecessors(curr):
                    if nxt in self.nodes and nxt not in visited:
                        queue.append((nxt, d + 1))

        for edge in self.edges:
            if edge.source in visited and edge.target in visited:
                subgraph.add_edge(edge)

        return subgraph


def build_graph(
    parsed_files: List[ParsedFile], resolved_map: Dict[str, List[ResolvedImport]]
) -> CodeGraph:
    graph = CodeGraph()
    parsed_module_names = {pf.module_name for pf in parsed_files}

    for pf in parsed_files:
        external_imports = []
        stdlib_imports = []
        internal_edges = []

        for r_imp in resolved_map.get(pf.module_name, []):
            if r_imp.status == "external" and r_imp.target_module is not None:
                external_imports.append(r_imp.target_module)
            elif r_imp.status == "stdlib" and r_imp.target_module is not None:
                stdlib_imports.append(r_imp.target_module)
            elif r_imp.status == "internal":
                # Only add if it's pointing to another actual module we parsed
                if (
                    r_imp.target_module != pf.module_name
                    and r_imp.target_module in parsed_module_names
                ):
                    internal_edges.append(
                        ImportEdge(
                            source=pf.module_name,
                            target=r_imp.target_module,
                            imported_names=r_imp.entry.names,
                        )
                    )

        # Filter duplicates in external
        external_imports = list(dict.fromkeys(external_imports))
        stdlib_imports = list(dict.fromkeys(stdlib_imports))

        node = FileNode(
            path=pf.path,
            module_name=pf.module_name,
            symbols=pf.symbols,
            docstring=pf.docstring,
            external_imports=external_imports,
            stdlib_imports=stdlib_imports,
        )
        graph.add_node(node)

        for edge in internal_edges:
            graph.add_edge(edge)

    return graph
