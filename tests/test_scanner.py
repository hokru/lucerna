import tempfile
from pathlib import Path
from lucerna.scanner import scan_directory, should_exclude


def test_should_exclude():
    root = Path("/project")
    excludes = ["venv", "*.pyc"]

    assert should_exclude(Path("/project/venv/lib"), root, excludes) is True
    assert should_exclude(Path("/project/main.pyc"), root, excludes) is True
    assert should_exclude(Path("/project/main.py"), root, excludes) is False


def test_lucernaignore_support():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create some files
        (tmp_path / "main.py").touch()
        (tmp_path / "foo.py").touch()
        (tmp_path / "bar.cpp").touch()

        # Write .lucernaignore
        with open(tmp_path / ".lucernaignore", "w", encoding="utf-8") as f:
            f.write("# ignore cpp files\n")
            f.write("*.cpp\n")
            f.write("foo.py\n")

        results = scan_directory(tmpdir)
        # Should only contain main.py
        rel_paths = {r[1] for r in results}
        assert "main.py" in rel_paths
        assert "foo.py" not in rel_paths
        assert "bar.cpp" not in rel_paths
