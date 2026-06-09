from lucerna.cpp_parser import parse_cpp_file


def test_parse_cpp_file():
    pf = parse_cpp_file(
        "tests/fixtures/cpp_bindings/bindings.cpp",
        "tests/fixtures/cpp_bindings/bindings.cpp",
    )

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


def test_cpp_class_chain_not_broken_by_internal_semicolons():
    # Write a temporary cpp file with inline semicolons inside chained method arguments
    import tempfile

    cpp_content = """
    BOOST_PYTHON_MODULE(test_chain) {
        class_<ChainClass>("ChainClass")
            .def("method_one", &ChainClass::method_one, "A doc; with semicolon")
            .def("method_two", &ChainClass::method_two)
        ;
    }
    """

    with tempfile.NamedTemporaryFile("w", suffix=".cpp", delete=False) as f:
        f.write(cpp_content)
        temp_name = f.name

    try:
        pf = parse_cpp_file(temp_name, "test_chain.cpp")
        assert pf is not None
        methods = [s for s in pf.symbols if s.kind == "method"]
        assert len(methods) == 2
        assert all(m.parent == "ChainClass" for m in methods)
    finally:
        import os

        os.unlink(temp_name)
