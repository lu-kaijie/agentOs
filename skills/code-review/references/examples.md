# Review Examples

## Good Finding

- `foo()` now returns early when `config` is empty, but the previous path still updated metrics. This changes behavior and may suppress reporting for empty-config requests.

## Weak Finding

- The code could be cleaner and easier to read.

## Good Missing-Test Callout

- The change adds a new branch for timeout handling, but no test covers the timeout path or the emitted error payload.
