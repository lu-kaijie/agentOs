## ADDED Requirements

### Requirement: Installed package must expose an `agentos` console command
The system SHALL expose an `agentos` console command through the installed Python package.

#### Scenario: Contributor launches the packaged command
- **WHEN** a contributor runs `agentos` after installing the package
- **THEN** the operating environment can resolve and execute the `agentos` command

### Requirement: The packaged command must default to the interactive shell experience
The system SHALL treat the persistent interactive shell as the default product entrypoint for the packaged `agentos` command.

#### Scenario: Contributor launches `agentos` with no subcommand
- **WHEN** a contributor runs `agentos` without additional arguments
- **THEN** the CLI starts the interactive shell instead of requiring a separate development-only launcher

### Requirement: The packaged CLI must preserve key operational subcommands
The system SHALL continue to expose a stable product command surface including `agentos shell`, `agentos run`, `agentos status`, `agentos session-show`, and `agentos watch`.

#### Scenario: Contributor launches a packaged subcommand
- **WHEN** a contributor runs `agentos status` or another primary operational subcommand
- **THEN** the packaged CLI executes the requested subcommand without requiring `python -m agentos.cli`

#### Scenario: Contributor uses session inspection from the packaged command
- **WHEN** a contributor runs `agentos session-show <session-id>` or `agentos watch <session-id>`
- **THEN** the packaged CLI preserves those capabilities under the same installed command surface instead of requiring a development-only launcher
