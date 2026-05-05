## ADDED Requirements

### Requirement: The project must be installable as a standard Python CLI package
The system SHALL define standard Python packaging metadata so contributors can install `agentOs` with common Python package workflows such as `pip install .`, `pip install -e .`, or `pipx install .`.

#### Scenario: Contributor installs the project from the repository root
- **WHEN** a contributor runs a supported Python installation command from the repository root
- **THEN** the project installs without requiring `PYTHONPATH=src` as a manual runtime step

### Requirement: Installed package must expose the runtime dependencies needed by the CLI
The system SHALL declare the dependencies required for the current CLI product path through its packaging metadata.

#### Scenario: Installed CLI starts after package installation
- **WHEN** a contributor installs the package and launches the CLI entrypoint
- **THEN** the installed environment contains the dependencies needed for the packaged CLI to start
