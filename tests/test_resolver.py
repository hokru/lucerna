from lucerna.resolver import _resolve_relative, resolve_imports
from lucerna.parser import ParsedFile, ImportEntry


def test_resolve_relative_normal():
    # Regular module import: level=1 inside mypkg.subpkg.algo
    target = _resolve_relative("mypkg.subpkg.algo", 1, "core", is_package=False)
    assert target == "mypkg.subpkg.core"

    # Go up 2 levels
    target = _resolve_relative("mypkg.subpkg.algo", 2, "core", is_package=False)
    assert target == "mypkg.core"


def test_resolve_relative_package_init():
    # Inside mypkg/subpkg/__init__.py, represented as package module "mypkg.subpkg".
    # Relative import level 1 'from . import algo' should resolve to 'mypkg.subpkg.algo'
    target = _resolve_relative("mypkg.subpkg", 1, "algo", is_package=True)
    assert target == "mypkg.subpkg.algo"


def test_resolve_imports_stdlib_vs_external():
    # Setup parsed files
    pf1 = ParsedFile(
        path="main.py",
        module_name="main",
        symbols=[],
        imports=[
            ImportEntry("os", [], None, False, 0),
            ImportEntry("requests", [], None, False, 0),
        ],
        docstring=None,
        is_package=False,
    )

    resolved = resolve_imports([pf1])
    imports = resolved["main"]

    os_imp = next(i for i in imports if i.entry.module == "os")
    requests_imp = next(i for i in imports if i.entry.module == "requests")

    assert os_imp.status == "stdlib"
    assert requests_imp.status == "external"
