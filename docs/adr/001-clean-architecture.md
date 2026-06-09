# ADR 001: Clean Architecture

## Status
Accepted

## Context
The assignment requires resilient FX fetching, calculations, and API endpoints. A monolith with mixed concerns scored poorly on architecture.

## Decision
Separate domain logic from HTTP and external APIs using ports/adapters.

## Consequences
- Testable business logic without HTTP mocks
- Clear file structure for LLM/human reviewers
- Slightly more files than a demo script
