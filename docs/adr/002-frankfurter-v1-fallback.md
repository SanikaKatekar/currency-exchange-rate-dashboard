# ADR 002: Frankfurter v1 Fallback URLs

## Status
Accepted

## Decision
Try legacy spec URLs first, then `/v1/` endpoints which are currently supported.

## Consequences
Handles API URL drift without breaking the assignment examples.
