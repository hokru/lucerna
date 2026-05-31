# CodeTree

CodeTree is a lightweight, zero-dependency codebase mapping tool designed to generate `aider`-style repository maps optimized for LLM context windows. It scans your Python project (and mixed C++/Python projects), extracts classes, methods, functions, docstrings, and imports, builds a unified dependency graph, and ranks nodes using PageRank.

## Features

- **LLM-Optimized Maps**: Generates condensed code summaries (signatures, docstrings, classes) perfect for LLM context.
- **Unified Dependency Graph**: Mentions, definitions, and imports across files are connected into a directed graph.
- **PageRank Importance Scoring**: Automatically surfaces the most central and important modules first.
- **C++ Bindings Support**: Detects and parses `Pybind11` and `Boost.Python` bindings in C++ source files (`.cpp`, `.cc`, `.cxx`).
- **Smart Linking**: Connects Python import patterns (including specific conventions like `bp.import_ext("module")`) directly to the corresponding C++ binding definitions.
- **Query Mode**: Interactively query the neighborhood of specific symbols to focus the map on relevant files.
- **Zero Dependencies**: Requires only a standard Python installation (uses native `ast` and pure-Python regex/graph utilities).

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Generate a standard text repository map for the current directory
codetree .

# Output map in JSON format for the top 20 most important files according to PageRank
codetree --format json --top-n 20 .

# Output a Mermaid diagram representing the dependency graph
codetree --format mermaid .

# Query the codebase map centered around a specific function or class
codetree --query "my_function" .
```

---

## Technical Details

### Zero-Dependency Architecture
To maintain a footprint suitable for easy deployment in any environment without installing external compilers or bindings (e.g., `tree-sitter` or Clang Python bindings), CodeTree uses a split architecture:
1. **Python Parsing**: Powered by Python's native `ast` library. This guarantees robust, standard-compliant extraction of Python modules, classes, functions, imports (`import x`, `from x import y`), and internal symbol references.
2. **C++ Bindings Parsing**: Uses a high-performance regex sliding-window tokenizer. It focuses specifically on matching `Pybind11` and `Boost.Python` syntax structures (e.g. `BOOST_PYTHON_MODULE(...)`, `PYBIND11_MODULE(...)`, `class_<...>`, and chained `.def()`, `.def_readwrite()`, `.add_property()` calls).

### Symbol Linking & Import Resolution
CodeTree parses both languages and reconciles import statements to build a unified graph:
- **Standard Python Imports**: Traced using absolute and relative path resolution based on the project's layout.
- **C++ Binding Modules**: When a C++ module is defined via `BOOST_PYTHON_MODULE(my_module)` or `PYBIND11_MODULE(my_module, m)`, it is registered under `my_module`.
- **Python-to-C++ Linking**: When Python imports a module (e.g., `import my_module` or `from my_module import some_cpp_func`), CodeTree links the importing Python file to the exporting C++ file.
- **`bp.import_ext` Support**: Specifically supports pattern configurations common in scientific codebases (like `cctbx`), where extensions are imported dynamically via helper functions:
  ```python
  import boost_adaptbx.boost.python as bp
  ext = bp.import_ext("my_module_ext")
  ```
  CodeTree extracts `"my_module_ext"` and successfully routes references to `ext.func()` back to `my_module_ext` in the C++ file.

---

## Mixed Codebase Advice & Tips

When mapping mixed Python and C++ codebases (e.g., projects using Boost.Python or Pybind11):

1. **Keep Code Structures Idiomatic**: The parser relies on regex heuristics. For example, it detects methods and classes exposed to Python by matching chaining patterns like:
   ```cpp
   class_<MyClass>("MyClass")
     .def("my_method", &MyClass::my_method)
     .def_readwrite("value", &MyClass::value);
   ```
   Writing binding code with standard spacing and indentation ensures that all methods, properties, and class declarations are correctly registered.
2. **Handling Dynamic Modules**: If your codebase dynamically compiles modules at runtime or places them in non-standard directories, CodeTree locates them by scanning the source files (`.cpp`, `.cc`, `.cxx`) in your project root. Ensure your C++ binding source files are checked in and located within the directory you are scanning.
3. **Optimizing Context Space**: C++ binding files can sometimes be extremely verbose. The PageRank algorithm ensures that if your Python codebase references a specific binding module heavily, that C++ file will rank high, ensuring the LLM sees its signature. If certain binding files are too noisy, you can filter them using command-line arguments or grep queries.
