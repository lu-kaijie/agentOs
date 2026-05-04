## ADDED Requirements

### Requirement: The project must define a local virtual environment workflow
The repository SHALL document and use a project-local virtual environment named `.venv-agentos` for dependency installation and local development.

#### Scenario: New contributor sets up the project
- **WHEN** a contributor follows the setup instructions
- **THEN** they create and use the `.venv-agentos` virtual environment instead of relying on global Python packages

### Requirement: Dependency files must pin exact versions
The project SHALL provide requirements files that pin dependency versions exactly for reproducible milestone builds.

#### Scenario: Dependency file is reviewed
- **WHEN** a contributor opens the requirements file used for setup
- **THEN** each declared package version is pinned to an explicit version value

### Requirement: The harness must separate execution boundaries from agent logic
The project SHALL define harness components so command execution responsibilities are separated from prompt and graph orchestration logic.

#### Scenario: Command execution path is inspected
- **WHEN** a contributor reviews the harness implementation
- **THEN** they can distinguish command execution code from agent reasoning and orchestration code
