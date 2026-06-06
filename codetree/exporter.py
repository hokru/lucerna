import json
from typing import Dict, Any
from .graph import CodeGraph

def _render_symbols(node, indent_str: str, include_docstrings: bool) -> list[str]:
    lines = []
    classes = {}
    functions = []
    
    constants = []
    
    for sym in node.symbols:
        if sym.kind == "class":
            classes[sym.name] = (sym, [])
        elif sym.kind in ("method", "async_method"):
            if sym.parent and sym.parent in classes:
                classes[sym.parent][1].append(sym)
            else:
                functions.append(sym)
        elif sym.kind in ("constant", "type_alias"):
            constants.append(sym)
        else:
            functions.append(sym)
            
    for cls_sym, methods in classes.values():
        sig = cls_sym.signature if cls_sym.signature != "()" else ""
        lines.append(f"{indent_str}class {cls_sym.name}{sig}:")
        if include_docstrings and cls_sym.docstring:
            doc = cls_sym.docstring.strip().split("\n")[0]
            lines.append(f"{indent_str}  # {doc}")
        for m in methods:
            async_prefix = "async " if m.kind == "async_method" else ""
            lines.append(f"{indent_str}  {async_prefix}def {m.name}{m.signature}")
            
    for f_sym in functions:
        async_prefix = "async " if f_sym.kind == "async_function" else ""
        lines.append(f"{indent_str}{async_prefix}def {f_sym.name}{f_sym.signature}")

    for c_sym in constants:
        lines.append(f"{indent_str}{c_sym.name}{c_sym.signature}")
    return lines

class TextMapExporter:
    def __init__(self, graph: CodeGraph, pagerank: Dict[str, float]):
        self.graph = graph
        self.pagerank = pagerank

    def export(self, top_n: int = None, include_docstrings: bool = False) -> str:
        sorted_modules = sorted(self.graph.nodes.keys(), key=lambda m: self.pagerank.get(m, 0), reverse=True)
        if top_n is not None:
            sorted_modules = sorted_modules[:top_n]

        lines = []
        for module in sorted_modules:
            node = self.graph.nodes[module]
            lines.append(f"{node.path}:")
            if include_docstrings and node.docstring:
                doc = node.docstring.strip().split("\n")[0]
                lines.append(f"  # {doc}")
            lines.extend(_render_symbols(node, "  ", include_docstrings))
            lines.append("") # Empty line between files
            
        return "\n".join(lines).strip()

class TreeExporter:
    def __init__(self, graph: CodeGraph, pagerank: Dict[str, float]):
        self.graph = graph
        self.pagerank = pagerank

    def export(self, top_n: int = None, include_docstrings: bool = False, show_rank: bool = False, relevance: Dict[str, float] = None) -> str:
        sorted_modules = sorted(self.graph.nodes.keys(), key=lambda m: self.pagerank.get(m, 0), reverse=True)
        if top_n is not None:
            sorted_modules = sorted_modules[:top_n]

        from pathlib import Path
        
        # Build tree structure
        tree = {}
        for module in sorted_modules:
            node = self.graph.nodes[module]
            parts = Path(node.path).parts
            current = tree
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current.setdefault("__files__", []).append(node)
                else:
                    current = current.setdefault(part, {})

        lines = []
        def _render_tree(current_dict, prefix=""):
            # Sort keys to put folders first, then __files__
            keys = sorted(k for k in current_dict.keys() if k != "__files__")
            files = current_dict.get("__files__", [])
            
            # Combine folders and files for proper drawing of last item
            items = []
            for k in keys:
                items.append(("folder", k, current_dict[k]))
            # sort files by path to be consistent
            files = sorted(files, key=lambda f: f.path)
            for f in files:
                items.append(("file", f.path, f))

            for i, (item_type, key, val) in enumerate(items):
                is_last = i == len(items) - 1
                branch = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                if item_type == "folder":
                    lines.append(f"{prefix}{branch}📁 {key}/")
                    _render_tree(val, next_prefix)
                else:
                    # It's a FileNode
                    node = val
                    rank_str = ""
                    if show_rank:
                        rank_str = f" [rank: {self.pagerank.get(node.module_name, 0):.4f}]"
                    
                    is_low_relevance = False
                    if relevance is not None:
                        # dim if relevance is low (< 0.1)
                        if relevance.get(node.module_name, 0) < 0.1:
                            is_low_relevance = True

                    filename = Path(node.path).name
                    lines.append(f"{prefix}{branch}📄 {filename}{rank_str}")
                    
                    if not is_low_relevance:
                        sym_lines = _render_symbols(node, next_prefix, include_docstrings)
                        lines.extend(sym_lines)

        _render_tree(tree)
        return "\n".join(lines).strip()

class JsonExporter:
    def __init__(self, graph: CodeGraph, pagerank: Dict[str, float]):
        self.graph = graph
        self.pagerank = pagerank
        
    def export(self) -> str:
        data: Dict[str, Any] = {"nodes": [], "edges": []}
        
        for module, node in self.graph.nodes.items():
            data["nodes"].append({
                "module": module,
                "path": node.path,
                "pagerank": self.pagerank.get(module, 0),
                "symbols": [{"name": s.name, "kind": s.kind, "signature": s.signature} for s in node.symbols],
                "external_imports": node.external_imports,
                "stdlib_imports": node.stdlib_imports,
                "docstring": node.docstring
            })
            
        for edge in self.graph.edges:
            data["edges"].append({
                "source": edge.source,
                "target": edge.target,
                "names": edge.imported_names
            })
            
        return json.dumps(data, indent=2)

class MermaidExporter:
    def __init__(self, graph: CodeGraph, pagerank: Dict[str, float]):
        self.graph = graph
        self.pagerank = pagerank
        
    def export(self, top_n: int = None) -> str:
        sorted_modules = sorted(self.graph.nodes.keys(), key=lambda m: self.pagerank.get(m, 0), reverse=True)
        if top_n is not None:
            valid_nodes = set(sorted_modules[:top_n])
        else:
            valid_nodes = set(sorted_modules)
            
        lines = ["flowchart TD"]
        
        # Add nodes
        for node_id in valid_nodes:
            # Escape for Mermaid
            display_name = node_id.replace('"', '\\"')
            lines.append(f'  {node_id.replace(".", "_")}["{display_name}"]')
            
        # Add edges
        for edge in self.graph.edges:
            if edge.source in valid_nodes and edge.target in valid_nodes:
                lines.append(f'  {edge.source.replace(".", "_")} --> {edge.target.replace(".", "_")}')
                
        return "\n".join(lines)
