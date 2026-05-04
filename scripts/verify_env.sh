#!/usr/bin/env bash

set -euo pipefail

python - <<'PY'
import os
import sys

required_prefix = ".venv-agentos"
venv = os.environ.get("VIRTUAL_ENV", "")

if not venv.endswith(required_prefix):
    raise SystemExit(
        f"Expected active virtual environment ending with {required_prefix!r}, got: {venv or '<none>'}"
    )

if sys.version_info[:2] != (3, 10):
    raise SystemExit(
        f"Expected Python 3.10.x for current milestone, got: {sys.version.split()[0]}"
    )

import langchain  # noqa: F401
import langgraph  # noqa: F401
import openai  # noqa: F401
import typer  # noqa: F401
from dotenv import load_dotenv  # noqa: F401
from pydantic import BaseModel  # noqa: F401

print("Environment verification passed.")
print(f"Python: {sys.version.split()[0]}")
print(f"Virtualenv: {venv}")
PY
