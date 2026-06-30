---
adr: 0001
status: accepted
title: Why MCP for database operations
---

# ADR 0001: Why MCP

## Context

Agent clients need a stable protocol for tools and resources.

## Decision

Use the official MCP Python SDK and expose database operations as Tools and Resources.

## Consequences

- Consistent integration with Claude Desktop, Cursor, and other MCP clients
- Explicit transport boundaries (stdio/http)
