filepath: phases/00-glossary.md
# Glossary — canonical terms

| Term | Meaning |
|---|---|
| **Connector** | Implementation of `mcpdb.db.base.Connector` for a single backend |
| **Backend** | "postgres", "mysql", "sqlite", "mongodb" — short identifiers |
| **Profile** | A named database in `mcpdb.yaml` (host, creds ref, mode, limits) |
| **Mode** | `read_only` (default) or `read_write` — operation class gate |
| **Policy** | Runtime decision object: allows/denies ops, enforces row/timeout caps |
| **Tool** | MCP-exposed callable: `db_query`, `db_introspect`, etc. |
| **Resource** | MCP-exposed data: `db://<profile>/tables`, `db://<profile>/schema/<t>` |
| **Transport** | `stdio` or `http` — only these two are supported |
| **Audit Entry** | Immutable record: `who, when, source, action, target, outcome` |
| **Gate** | An automated check (§3 of DIRECTIVE.md) that must pass |
| **DoD** | Definition of Done for the active phase — must be 100% green |
| **Context** | Typed object passed to every tool carrying policy, conn, audit hook |
| **Cap** | Numerical limit: row count, timeout, payload bytes, rate tokens |
| **SecretRef** | A non-secret reference like `${env:PG_PASSWORD}` or `${vault:...}` |
| **Operation Class** | One of READ, WRITE, ADMIN — used by policy to gate tools |

Use these terms verbatim in code identifiers, docstrings, and audit entries. Do not invent synonyms (e.g., don't use "driver", "DAO", "repository").
