import argparse
import sys
from .scanner import scan_directory, DEFAULT_EXCLUDES
from .parser import parse_file
from .resolver import resolve_imports
from .graph import build_graph
from .ranker import calculate_pagerank
from .exporter import TextMapExporter, JsonExporter, MermaidExporter, TreeExporter


def main():
    parser = argparse.ArgumentParser(
        description="CodeTree: A Python codebase mapping tool for LLMs"
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "mermaid", "tree"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--top-n", type=int, help="Limit output to top N files by PageRank"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Glob patterns to exclude (can be specified multiple times)",
    )
    parser.add_argument(
        "--query", help="Semantic search query to co-rank files by relevance"
    )
    parser.add_argument(
        "--neighborhood", help="Show the local neighborhood of a module name or symbol"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Depth of neighborhood traversal (default: 1)",
    )
    parser.add_argument(
        "--max-chars", type=int, help="Limit output size by cumulative character count"
    )
    parser.add_argument(
        "--python-only", action="store_true", help="Skip scanning C++ source files"
    )
    parser.add_argument(
        "--include-docstrings",
        action="store_true",
        help="Include first-line docstrings in text output",
    )
    parser.add_argument(
        "--show-rank", action="store_true", help="Show PageRank scores in tree output"
    )
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
        if file_type == "python":
            pf = parse_file(abs_path, rel_path)
        elif file_type == "cpp":
            if args.python_only:
                continue
            pf = parse_cpp_file(abs_path, rel_path)
        else:
            continue

        if pf is None:
            print(f"Warning: Failed to parse {rel_path}", file=sys.stderr)
        else:
            parsed_files.append(pf)

    # 3. Resolve
    resolved_map = resolve_imports(parsed_files)

    # 4. Graph
    graph = build_graph(parsed_files, resolved_map)

    # 5. Rank
    pagerank = calculate_pagerank(graph)

    # Handle Query Mode
    relevance = None
    if args.query:
        from .search import score_query, combine_scores

        relevance = score_query(graph, args.query)
        pagerank = combine_scores(relevance, pagerank, alpha=0.6)

    # Handle Neighborhood Mode
    if args.neighborhood:
        depth = args.depth
        if args.neighborhood in graph.nodes:
            # Query by module name
            graph = graph.neighborhood(args.neighborhood, depth=depth)
        else:
            # Try to find a symbol matching
            found_module = None
            for module, node in graph.nodes.items():
                if any(sym.name == args.neighborhood for sym in node.symbols):
                    found_module = module
                    break

            if found_module:
                graph = graph.neighborhood(found_module, depth=depth)
            else:
                print(
                    f"Could not find module or symbol: {args.neighborhood}",
                    file=sys.stderr,
                )
                return

    # 6. Export
    if args.format == "text":
        exporter = TextMapExporter(graph, pagerank)
        output = exporter.export(
            top_n=args.top_n, include_docstrings=args.include_docstrings
        )
    elif args.format == "json":
        exporter = JsonExporter(graph, pagerank)
        output = exporter.export()
    elif args.format == "mermaid":
        exporter = MermaidExporter(graph, pagerank)
        output = exporter.export(top_n=args.top_n)
    else:  # tree
        exporter = TreeExporter(graph, pagerank)
        output = exporter.export(
            top_n=args.top_n,
            include_docstrings=args.include_docstrings,
            show_rank=args.show_rank,
            relevance=relevance,
        )

    # Budget check
    if args.max_chars is not None and len(output) > args.max_chars:
        # If output exceeds budget, we successively prune the lowest ranked nodes
        sorted_modules = sorted(
            graph.nodes.keys(), key=lambda m: pagerank.get(m, 0), reverse=True
        )
        # Keep pruning from the end until output length fits, or only 1 remains
        while len(sorted_modules) > 1:
            removed = sorted_modules.pop()
            # Construct a sub-graph with only the remaining modules
            from .graph import CodeGraph

            subgraph = CodeGraph()
            for m in sorted_modules:
                subgraph.add_node(graph.nodes[m])
            for edge in graph.edges:
                if edge.source in sorted_modules and edge.target in sorted_modules:
                    subgraph.add_edge(edge)

            # Re-export with the subgraph
            if args.format == "text":
                sub_exporter = TextMapExporter(subgraph, pagerank)
                output = sub_exporter.export(
                    top_n=args.top_n, include_docstrings=args.include_docstrings
                )
            elif args.format == "json":
                sub_exporter = JsonExporter(subgraph, pagerank)
                output = sub_exporter.export()
            elif args.format == "mermaid":
                sub_exporter = MermaidExporter(subgraph, pagerank)
                output = sub_exporter.export(top_n=args.top_n)
            else:
                sub_exporter = TreeExporter(subgraph, pagerank)
                output = sub_exporter.export(
                    top_n=args.top_n,
                    include_docstrings=args.include_docstrings,
                    show_rank=args.show_rank,
                    relevance=relevance,
                )

            if len(output) <= args.max_chars:
                break

    # 7. Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
    else:
        print(output)


if __name__ == "__main__":
    main()
