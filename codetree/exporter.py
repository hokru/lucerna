import json
from typing import Dict, Any
from .graph import CodeGraph

class TextMapExporter:
    def __init__(self, graph: CodeGraph, pagerank: Dict[str, float]):
        self.graph = graph
        self.pagerank = pagerank

    def export(self, top_n: int = None, include_docstrings: bool = False) -> str:
        # Sort nodes by PageRank descending
        sorted_modules = sorted(self.graph.nodes.keys(), key=lambda m: self.pagerank.get(m, 0), reverse=True)
        
        if top_n is not None:
            sorted_modules = sorted_modules[:top_n]
            
        # Optional: Re-sort by path for display so it looks like a tree
        # sorted_modules = sorted(sorted_modules, key=lambda m: self.graph.nodes[m].path)

        lines = []
        for module in sorted_modules:
            node = self.graph.nodes[module]
            lines.append(f"{node.path}:")
            
            if include_docstrings and node.docstring:
                doc = node.docstring.strip().split("\n")[0]
                lines.append(f"  # {doc}")
                
            # Print symbols
            # Group by class vs function
            # Since we want a nice hierarchy, let's group methods under classes
            classes = {}
            functions = []
            
            for sym in node.symbols:
                if sym.kind == "class":
                    classes[sym.name] = (sym, [])
                elif sym.kind in ("method", "async_method"):
                    if sym.parent and sym.parent in classes:
                        classes[sym.parent][1].append(sym)
                    else:
                        functions.append(sym)
                else:
                    functions.append(sym)
                    
            for cls_sym, methods in classes.values():
                sig = cls_sym.signature if cls_sym.signature != "()" else ""
                lines.append(f"  class {cls_sym.name}{sig}:")
                if include_docstrings and cls_sym.docstring:
                    doc = cls_sym.docstring.strip().split("\n")[0]
                    lines.append(f"    # {doc}")
                for m in methods:
                    async_prefix = "async " if m.kind == "async_method" else ""
                    lines.append(f"    {async_prefix}def {m.name}{m.signature}")
                    
            for f_sym in functions:
                async_prefix = "async " if f_sym.kind == "async_function" else ""
                lines.append(f"  {async_prefix}def {f_sym.name}{f_sym.signature}")
                
            lines.append("") # Empty line between files
            
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
                "external_imports": node.external_imports
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
