PYTHON := .venv-agentos/bin/python
PYTEST := .venv-agentos/bin/pytest

.PHONY: status run run-model shell shell-model run-knowledge exec bg-run bg-list workspace-create workspace-list unit-list task-list knowledge-list context-demo test verify-env

status:
	PYTHONPATH=src $(PYTHON) -m agentos.cli status

run:
	PYTHONPATH=src $(PYTHON) -m agentos.cli run "run: pwd"

run-model:
	PYTHONPATH=src $(PYTHON) -m agentos.cli run "请读取 README.md，并用两句话总结这个项目当前是什么。" --model --session-id demo-model

shell:
	PYTHONPATH=src $(PYTHON) -m agentos.cli shell --session-id demo-shell

shell-model:
	PYTHONPATH=src $(PYTHON) -m agentos.cli shell --session-id demo-model-shell

run-knowledge:
	PYTHONPATH=src $(PYTHON) -m agentos.cli run "knowledge: langgraph-runtime"

exec:
	PYTHONPATH=src $(PYTHON) -m agentos.cli exec pwd

bg-run:
	PYTHONPATH=src $(PYTHON) -m agentos.cli bg-run "bash -lc 'sleep 1 && printf done'"

bg-list:
	PYTHONPATH=src $(PYTHON) -m agentos.cli bg-list

workspace-create:
	PYTHONPATH=src $(PYTHON) -m agentos.cli workspace-create demo

workspace-list:
	PYTHONPATH=src $(PYTHON) -m agentos.cli workspace-list

unit-list:
	PYTHONPATH=src $(PYTHON) -m agentos.cli unit-list

task-list:
	PYTHONPATH=src $(PYTHON) -m agentos.cli task-list

knowledge-list:
	PYTHONPATH=src $(PYTHON) -m agentos.cli knowledge-list

context-demo:
	PYTHONPATH=src $(PYTHON) -m agentos.cli context-demo

test:
	$(PYTEST) tests/test_bootstrap.py tests/test_cli.py tests/test_imports.py tests/test_harness_execution.py tests/test_langgraph_runtime.py tests/test_task_manager.py tests/test_task_cli.py tests/test_knowledge_loader.py tests/test_context_manager.py tests/test_context_cli.py tests/test_background_manager.py tests/test_workspace_manager.py tests/test_execution_control_cli.py tests/test_coordination_manager.py tests/test_coordination_cli.py tests/test_tool_registry.py tests/test_packaged_cli.py

verify-env:
	bash scripts/verify_env.sh
