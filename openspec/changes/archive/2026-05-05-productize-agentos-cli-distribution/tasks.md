## 1. Packaging Foundation

- [x] 1.1 Add standard Python packaging metadata for `agentOs`
- [x] 1.2 Expose an `agentos` console script entrypoint through the package
- [x] 1.3 Verify the package can be installed locally without `PYTHONPATH=src`

## 2. Product CLI Entry

- [x] 2.1 Make `agentos` default to the interactive shell experience
- [x] 2.2 Preserve the stable packaged command surface: `shell`, `run`, `status`, `session-show`, and `watch`
- [x] 2.3 Add a packaged CLI smoke test for install-and-launch behavior
- [x] 2.4 Verify and document the exact packaged behavior of `agentos`, `agentos shell`, `agentos run`, `agentos status`, `agentos session-show`, and `agentos watch`

## 3. Configuration Bootstrap

- [x] 3.1 Commit a maintainable `.env.example` product template
- [x] 3.2 Add clear user-facing guidance for missing product configuration on startup
- [x] 3.3 Document the role-based three-tier model configuration in the installation flow

## 4. Docs And Productization Finish

- [x] 4.1 Update README to make installation-first usage the main path
- [x] 4.2 Separate product usage guidance from development-only commands
- [x] 4.3 Add a final verification checklist for `pip install -e .` and `agentos` startup

## 5. Terminal Product UI

- [x] 5.1 Add a first product-oriented terminal presentation layer for the packaged shell, preferably using `textual`
- [x] 5.2 Make status, tool activity, and agent output visually easier to distinguish during shell interaction
- [x] 5.3 Add a shell presentation smoke test or documented verification flow for the beautified CLI or TUI
- [x] 5.4 Ensure the packaged shell opens into a stable layout with a persistent input area plus a separated conversation/activity region
