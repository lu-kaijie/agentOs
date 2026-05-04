PYTHON := .venv-agentos/bin/python
PYTEST := .venv-agentos/bin/pytest

.PHONY: status run exec test verify-env

status:
	PYTHONPATH=src $(PYTHON) -m agentos.cli status

run:
	PYTHONPATH=src $(PYTHON) -m agentos.cli run

exec:
	PYTHONPATH=src $(PYTHON) -m agentos.cli exec pwd

test:
	$(PYTEST) tests/test_bootstrap.py tests/test_cli.py tests/test_imports.py tests/test_harness_execution.py

verify-env:
	bash scripts/verify_env.sh
