## ADDED Requirements

### Requirement: The product must provide a committed environment template
The system SHALL provide a committed example environment file so users can prepare runtime configuration before launching the installed CLI.

#### Scenario: Contributor prepares local configuration
- **WHEN** a contributor sets up the project for first use
- **THEN** they can copy a committed environment template and fill in required values such as model credentials

### Requirement: The packaged CLI must provide user-facing guidance for missing configuration
The system SHALL provide a clear user-facing message when required runtime configuration for the product path is missing.

#### Scenario: Contributor launches model-backed shell without required configuration
- **WHEN** a contributor starts the product entrypoint without the required model configuration
- **THEN** the CLI explains what configuration is missing and how to prepare it instead of only surfacing a low-level exception

### Requirement: Product documentation must describe installation-first usage
The system SHALL document installation and startup using the packaged command surface as the primary usage path.

#### Scenario: Contributor reads the repository usage guide
- **WHEN** a contributor follows the main installation and startup documentation
- **THEN** they are guided toward installing the package and launching `agentos` directly
