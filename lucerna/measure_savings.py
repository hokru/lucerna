import os
import subprocess
import sys

try:
    import tiktoken
except ImportError:
    print(
        "Error: tiktoken is not installed. Install it with: pip install tiktoken",
        file=sys.stderr,
    )
    sys.exit(1)


def get_raw_codebase_content(root_dir):
    """Gathers the text content of all Python and C++ files in the directory, respecting basic excludes."""
    content = []
    excludes = {
        ".git",
        "venv",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
    }

    for root, dirs, files in os.walk(root_dir):
        # Prune excludes in-place
        dirs[:] = [d for d in dirs if d not in excludes]
        for file in files:
            if file.endswith((".py", ".cpp", ".cc", ".cxx", ".c")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content.append(f.read())
                except Exception:
                    pass
    return "\n".join(content)


def get_lucerna_output(root_dir):
    """Runs lucerna command and returns the stdout string."""
    cmd = [sys.executable, "-m", "lucerna.cli", root_dir, "--format", "text"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout


def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    print(f"Analyzing codebase in '{root_dir}'...")

    raw_text = get_raw_codebase_content(root_dir)
    map_text = get_lucerna_output(root_dir)

    # Use cl100k_base (standard tokenization for GPT-4/GPT-3.5)
    encoding = tiktoken.get_encoding("cl100k_base")

    raw_tokens = len(encoding.encode(raw_text))
    map_tokens = len(encoding.encode(map_text))

    saved_tokens = raw_tokens - map_tokens
    saving_percentage = (saved_tokens / raw_tokens) * 100 if raw_tokens > 0 else 0

    print("\n" + "=" * 40)
    print("              TOKEN SAVINGS REPORT")
    print("=" * 40)
    print(f"Raw Codebase Tokens:   {raw_tokens:,}")
    print(f"Lucerna Map Tokens:    {map_tokens:,}")
    print(f"Tokens Saved:          {saved_tokens:,}")
    print(f"Savings Percentage:    {saving_percentage:.2f}%")
    print("=" * 40)


if __name__ == "__main__":
    main()
