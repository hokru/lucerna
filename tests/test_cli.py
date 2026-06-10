import sys
import os
import subprocess


def test_cli_basic():
    # Run CLI on fixtures package
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")

    # We can run cli via python -m lucerna.cli or using main() directly,
    # but subprocess is safer to test the actual script execution.
    cmd = [sys.executable, "-m", "lucerna.cli", fixtures_dir, "--format", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0
    assert "mypkg.core" in res.stdout
    assert "mypkg.utils" in res.stdout


def test_cli_max_chars():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    cmd = [sys.executable, "-m", "lucerna.cli", fixtures_dir, "--max-chars", "200"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0
    # Length of output should be strictly less than or equal to max-chars
    assert len(res.stdout) <= 200


def test_cli_python_only():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")

    # With --python-only, C++ files are excluded
    cmd = [
        sys.executable,
        "-m",
        "lucerna.cli",
        fixtures_dir,
        "--python-only",
        "--format",
        "json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0
    import json

    data = json.loads(res.stdout)
    modules = {node["module"] for node in data["nodes"]}
    assert "my_cpp_ext" not in modules
