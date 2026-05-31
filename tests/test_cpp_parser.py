import pytest
from codetree.cpp_parser import parse_cpp_file

def test_parse_cpp_file():
    pf = parse_cpp_file("tests/fixtures/cpp_bindings/bindings.cpp", "tests/fixtures/cpp_bindings/bindings.cpp")
    
    assert pf is not None
    assert pf.module_name == "my_cpp_ext"
    assert len(pf.symbols) == 6
    
    classes = [s for s in pf.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "MyClass"
    
    methods = [s for s in pf.symbols if s.kind == "method"]
    assert len(methods) == 2
    assert methods[0].name == "method_a"
    assert methods[0].parent == "MyClass"
    assert methods[1].name == "method_b"
    
    properties = [s for s in pf.symbols if s.kind == "property"]
    assert len(properties) == 2
    assert properties[0].name == "my_prop"
    assert properties[0].parent == "MyClass"
    assert properties[1].name == "verbose"
    assert properties[1].parent == "MyClass"
    
    functions = [s for s in pf.symbols if s.kind == "function"]
    assert len(functions) == 1
    assert functions[0].name == "free_func"
    assert functions[0].parent is None
