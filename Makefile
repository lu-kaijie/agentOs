PYTHON := .venv-agentos/bin/python
PYTEST := .venv-agentos/bin/pytest

.PHONY: status run exec task-list test verify-env

status:
	PYTHONPATH=src $(PYTHON) -m agentos.cli status

run:
	PYTHONPATH=src $(PYTHON) -m agentos.cli run "run: pwd"

exec:
	PYTHONPATH=src $(PYTHON) -m agentos.cli exec pwd

task-list:
	PYTHONPATH=src $(PYTHON) -m agentos.cli task-list

test:
	$(PYTEST) tests/test_bootstrap.py tests/test_cli.py tests/test_imports.py tests/test_harness_execution.py tests/test_langgraph_runtime.py tests/test_task_manager.py tests/test_task_cli.py

verify-env:
	bash scripts/verify_env.sh
