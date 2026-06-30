---
adr: 0002
status: accepted
title: Why the stack is locked
---

# ADR 0002: Locked stack

## Context

Frequent library swaps create drift and security review gaps.

## Decision

Use a locked stack: uv, mcp SDK, starlette/uvicorn, pydantic v2, SQLAlchemy async, motor, structlog, OTEL, and strict test/quality gates.

## Consequences

- Predictable operational behavior
- Repeatable security posture
- Faster onboarding through stable tooling
