---
adr: 0003
status: accepted
title: Why security defaults are deny-first
---

# ADR 0003: Security defaults

## Context

mcpdb targets production-adjacent data systems.

## Decision

Default to read_only Mode, deny writes unless explicitly allowed, and require clear warnings for unsafe network/auth combinations.

## Consequences

- Fewer accidental data modifications
- Stronger baseline against OWASP A01 and A05 risks
