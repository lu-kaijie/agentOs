#!/usr/bin/env python3
"""Example helper script for collecting diff-oriented review context."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    workspace = Path.cwd()
    top_level = sorted(path.name for path in workspace.iterdir())[:12]
    print("workspace_top_level:")
    for item in top_level:
        print(f"- {item}")


if __name__ == "__main__":
    main()
