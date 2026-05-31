import os
from pathlib import Path
from codetree.scanner import scan_directory
from codetree.parser import parse_file
from codetree.resolver import resolve_imports
from codetree.graph import build_graph
from codetree.ranker import calculate_pagerank

def test_codetree_end_to_end():
    # Setup paths
    root_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    
    # Scan
    files = scan_directory(root_dir)
    assert len(files) == 8
    parsed_files = []
    from codetree.cpp_parser import parse_cpp_file
    for abs_path, rel_path, file_type in files:
        if file_type == 'python':
            pf = parse_file(abs_path, rel_path)
        elif file_type == 'cpp':
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
