import os
from lucerna.scanner import scan_directory
from lucerna.parser import parse_file
from lucerna.resolver import resolve_imports
from lucerna.graph import build_graph
from lucerna.ranker import calculate_pagerank


def test_lucerna_end_to_end():
    # Setup paths
    root_dir = os.path.join(os.path.dirname(__file__), "fixtures")

    # Scan
    files = scan_directory(root_dir)
    assert len(files) == 8
    parsed_files = []
    from lucerna.cpp_parser import parse_cpp_file

    for abs_path, rel_path, file_type in files:
        if file_type == "python":
            pf = parse_file(abs_path, rel_path)
        elif file_type == "cpp":
            pf = parse_cpp_file(abs_path, rel_path)
        else:
            continue
        if pf:
            parsed_files.append(pf)

    assert len(parsed_files) == 8

    # Check parser for core.py
    core_pf = next(pf for pf in parsed_files if pf.module_name == "mypkg.core")
    assert any(s.name == "MyClass" for s in core_pf.symbols)

    # Check parser for utils.py
    utils_pf = next(pf for pf in parsed_files if pf.module_name == "mypkg.utils")
    helper_sym = next(s for s in utils_pf.symbols if s.name == "helper")
    assert helper_sym.docstring == "Helps with something."
    assert "x: int" in helper_sym.signature
    assert "-> str" in helper_sym.signature

    # Resolve imports
    resolved_map = resolve_imports(parsed_files)

    # core.py should resolve .utils to mypkg.utils
    core_resolves = resolved_map["mypkg.core"]
    utils_import = next(r for r in core_resolves if r.target_module == "mypkg.utils")
    assert utils_import.status == "internal"

    # algo.py should resolve ..core to mypkg.core
    algo_resolves = resolved_map["mypkg.subpkg.algo"]
    core_import = next(r for r in algo_resolves if r.target_module == "mypkg.core")
    assert core_import.status == "internal"

    # utils.py should resolve sys to stdlib
    utils_resolves = resolved_map["mypkg.utils"]
    sys_import = next(r for r in utils_resolves if r.target_module == "sys")
    assert sys_import.status == "stdlib"

    # Graph
    graph = build_graph(parsed_files, resolved_map)
    assert "mypkg.core" in graph.nodes

    # Check that None is not in any external/stdlib imports
    for node in graph.nodes.values():
        assert None not in node.external_imports
        assert None not in node.stdlib_imports

    # Check that stdlib imports are correct
    utils_node = graph.nodes["mypkg.utils"]
    assert "sys" in utils_node.stdlib_imports
    assert "os.path" in utils_node.stdlib_imports

    # Check edges (main -> mypkg.core, main -> mypkg.subpkg.algo, algo -> core, core -> utils)
    assert "mypkg.utils" in graph.successors("mypkg.core")
    assert "mypkg.core" in graph.successors("mypkg.subpkg.algo")

    # Ranker
    pagerank = calculate_pagerank(graph)

    # utils.py should rank highest because it's at the bottom of the dependency chain
    # and everything depends on it (algo -> core -> utils, main -> core -> utils)
    assert pagerank["mypkg.utils"] > pagerank["main"]


def test_search_and_combine():
    from lucerna.graph import CodeGraph, FileNode
    from lucerna.parser import ParsedSymbol
    from lucerna.search import score_query, combine_scores

    graph = CodeGraph()
    node1 = FileNode(
        "pkg/utils.py",
        "pkg.utils",
        [ParsedSymbol("helper", "function", 1, "()", "Helps with something", [], None)],
        "Utilities",
        [],
        [],
    )
    node2 = FileNode(
        "pkg/core.py",
        "pkg.core",
        [ParsedSymbol("MyClass", "class", 1, "()", "Core class", [], None)],
        "Core logic",
        [],
        [],
    )
    graph.add_node(node1)
    graph.add_node(node2)

    relevance = score_query(graph, "utils helper")

    # node1 has "utils" in path, "helper" in symbol name
    # node2 has neither
    assert relevance["pkg.utils"] > 0
    assert relevance["pkg.core"] == 0

    pagerank = {"pkg.utils": 0.8, "pkg.core": 0.2}
    combined = combine_scores(relevance, pagerank, alpha=0.5)

    assert combined["pkg.utils"] > 0
    assert combined["pkg.core"] > 0
    # pkg.utils should have high relevance and high pagerank
    assert combined["pkg.utils"] > combined["pkg.core"]


def test_tree_exporter():
    from lucerna.graph import CodeGraph, FileNode
    from lucerna.parser import ParsedSymbol
    from lucerna.exporter import TreeExporter

    graph = CodeGraph()
    node1 = FileNode(
        "pkg/utils.py",
        "pkg.utils",
        [ParsedSymbol("helper", "function", 1, "()", "Helps", [], None)],
        None,
        [],
        [],
    )
    graph.add_node(node1)

    pagerank = {"pkg.utils": 1.0}

    exporter = TreeExporter(graph, pagerank)
    out = exporter.export(show_rank=True)

    assert "📁 pkg/" in out
    assert "└── 📄 utils.py [rank: 1.0000]" in out
    assert "    def helper()" in out

    # Test low relevance collapse
    relevance = {"pkg.utils": 0.05}  # < 0.1
    out_collapse = exporter.export(relevance=relevance)
    assert "└── 📄 utils.py" in out_collapse
    assert "def helper()" not in out_collapse


def test_json_exporter_fields():
    from lucerna.graph import CodeGraph, FileNode
    from lucerna.exporter import JsonExporter

    graph = CodeGraph()
    node = FileNode(
        path="pkg/utils.py",
        module_name="pkg.utils",
        symbols=[],
        docstring="Module documentation",
        external_imports=["numpy"],
        stdlib_imports=["os"],
    )
    graph.add_node(node)

    exporter = JsonExporter(graph, {"pkg.utils": 1.0})
    out = exporter.export()

    import json

    data = json.loads(out)
    node_data = data["nodes"][0]
    assert node_data["docstring"] == "Module documentation"
    assert "os" in node_data["stdlib_imports"]


def test_parser_constants_and_all():
    import ast
    from lucerna.parser import CodeVisitor

    source = """
__all__ = ['foo', 'BAR']
MY_CONSTANT = 42
NormalVar = 10
type MyAlias = str | int
"""
    tree = ast.parse(source)
    visitor = CodeVisitor()
    visitor.visit(tree)

    names = {s.name: s for s in visitor.symbols}
    assert "__all__" in names
    assert names["__all__"].kind == "constant"
    assert "MY_CONSTANT" in names
    assert names["MY_CONSTANT"].kind == "constant"
    assert "NormalVar" not in names  # Should be excluded because not uppercase
    assert "MyAlias" in names
    assert names["MyAlias"].kind == "type_alias"
