# Harness Executor Notes

- Runtime code should not call subprocess directly.
- Execution boundaries belong in the harness layer.
- Structured execution results make later tracing and retries easier.
