import argparse
import sys
from pathlib import Path
from .scanner import scan_directory, DEFAULT_EXCLUDES
from .parser import parse_file
from .resolver import resolve_imports
from .graph import build_graph
from .ranker import calculate_pagerank
from .exporter import TextMapExporter, JsonExporter, MermaidExporter

def main():
    parser = argparse.ArgumentParser(description="CodeTree: A Python codebase mapping tool for LLMs")
    parser.add_argument("root", nargs="?", default=".", help="Root directory to scan (default: current directory)")
    parser.add_argument("--format", choices=["text", "json", "mermaid"], default="text", help="Output format")
    parser.add_argument("--top-n", type=int, help="Limit output to top N files by PageRank")
    parser.add_argument("--exclude", action="append", help="Glob patterns to exclude (can be specified multiple times)")
    parser.add_argument("--query", help="Show the local neighborhood of a module name")
    parser.add_argument("--include-docstrings", action="store_true", help="Include first-line docstrings in text output")
    parser.add_argument("--output", help="Write output to a file instead of stdout")
    
    args = parser.parse_args()
    
    excludes = DEFAULT_EXCLUDES.copy()
    if args.exclude:
        excludes.extend(args.exclude)
        
    # 1. Scan
    py_files = scan_directory(args.root, excludes)
    if not py_files:
        print(f"No Python files found in {args.root}", file=sys.stderr)
        return
        
    # Parse all files
    parsed_files = []
    from .cpp_parser import parse_cpp_file
    for abs_path, rel_path, file_type in py_files:
        if file_type == 'python':
            pf = parse_file(abs_path, rel_path)
        elif file_type == 'cpp':
            pf = parse_cpp_file(abs_path, rel_path)
        else:
            continue
            
        if pf:
            parsed_files.append(pf)
            
    # 3. Resolve
    resolved_map = resolve_imports(parsed_files)
    
    # 4. Graph
    graph = build_graph(parsed_files, resolved_map)
    
    # 5. Rank
    pagerank = calculate_pagerank(graph)
    
    # Handle Query Mode
    if args.query:
        if args.query in graph.nodes:
            # Query by module name
            graph = graph.neighborhood(args.query, depth=1)
        else:
            # Try to find a symbol matching
            found_module = None
            for module, node in graph.nodes.items():
                if any(sym.name == args.query for sym in node.symbols):
                    found_module = module
                    break
            
            if found_module:
                graph = graph.neighborhood(found_module, depth=1)
            else:
                print(f"Could not find module or symbol: {args.query}", file=sys.stderr)
                return

    # 6. Export
    if args.format == "text":
        exporter = TextMapExporter(graph, pagerank)
        output = exporter.export(top_n=args.top_n, include_docstrings=args.include_docstrings)
    elif args.format == "json":
        exporter = JsonExporter(graph, pagerank)
        output = exporter.export()
    else:  # mermaid
        exporter = MermaidExporter(graph, pagerank)
        output = exporter.export(top_n=args.top_n)
        
    # 7. Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
    else:
        print(output)

if __name__ == "__main__":
    main()
