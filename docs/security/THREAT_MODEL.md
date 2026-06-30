# THREAT MODEL

Document status: reviewed
Owner: mcpdb maintainers
Review cadence: each release

## Sign-off

- Primary reviewer: Levent Ozparlak
- Secondary reviewer: Pending maintainer review

## System components

1. CLI entrypoints (`serve`, `doctor`, `config validate`, `audit`, `repl`)
2. MCP server and Tool handlers
3. Connector layer (SQL + MongoDB)
4. Config + SecretRef loader
5. Security controls (auth, authz, rate limit)
6. Observability + Audit Entry chain
7. Release and supply-chain pipeline

## STRIDE analysis

| Component | Threat | Mitigation | Residual risk | Status |
|---|---|---|---|---|
| CLI | Spoofing via local shell injection | Strict arg parsing and no shell command execution | User shell compromise remains | accepted |
| CLI | Tampering of config path | Typed validation and explicit file checks | Malicious local files possible | accepted |
| CLI | Repudiation of operator actions | Audit Entry for config and serve actions | Local-only executions may lack identity context | open |
| CLI | Information disclosure in logs | structlog redaction rules and no plaintext SecretRef values | Misconfigured log sinks may leak metadata | mitigated |
| CLI | DoS via repeated invocations | lightweight process and rate limits at HTTP path | Local machine resource exhaustion remains | accepted |
| CLI | Privilege escalation via write operations | Mode defaults to read_only and Policy denies writes by default | Misconfiguration can still enable writes | mitigated |
| MCP server | Spoofing of callers on HTTP | bearer token checks with issuer/audience | token key management outside app boundary | open |
| MCP server | Tampering with Tool payload | pydantic validation + Operation Class checks | malformed but valid payloads still consume compute | mitigated |
| MCP server | Repudiation of Tool use | Audit Entry includes who/when/source/action/outcome | anonymous callers on misconfigured auth | open |
| MCP server | Information disclosure from errors | mapped errors hide internals for client surface | debug logs can expose details if enabled | mitigated |
| MCP server | DoS through expensive queries | query timeout + max rows + payload Caps | backend-level exhaustion possible | mitigated |
| MCP server | Elevation through admin Tool misuse | default deny for ADMIN Operation Class | operator misconfiguration risk | mitigated |
| Connector layer | Spoofing of backend endpoints | explicit Profile config and tested connectors | DNS poisoning outside app control | accepted |
| Connector layer | SQL/Mongo injection tampering | parameterized SQL and Mongo operator allow-list | unknown backend parser edge cases | mitigated |
| Connector layer | Repudiation of backend mutations | audit logging for write attempts and outcomes | DB-native logs may diverge | open |
| Connector layer | Info disclosure via result sets | row/payload Caps and allow-listing | sensitive data in allowed columns remains | accepted |
| Connector layer | DoS via slow queries | timeout Caps and cancellation behavior | lock contention in DB remains | mitigated |
| Connector layer | Elevation by unsafe operation class mapping | explicit Operation Class to Policy decision | policy bugs in future changes | open |
| Config loader | Spoofing of secret sources | SecretRef format validation | external secret provider spoofing | accepted |
| Config loader | Tampering with env vars | startup validation and required field checks | host compromise bypasses app controls | accepted |
| Config loader | Repudiation of config changes | config-change Audit Entry hooks | direct file edits outside app flow | open |
| Config loader | Info disclosure of secrets | do not log secret values | accidental debug prints remain possible | mitigated |
| Config loader | DoS by invalid config | fail fast on invalid schema | repeated restart loops | accepted |
| Config loader | Elevation by unsafe defaults | secure defaults documented and tested | user override can weaken posture | mitigated |
| Security controls | Spoofing auth tokens | audience/issuer checks and signature validation | weak upstream IdP policy | accepted |
| Security controls | Tampering bypass attempts | deny-first authz and operation gating | future regressions if tests removed | mitigated |
| Security controls | Repudiation of denied access | audit denied outcomes | external correlation IDs may be missing | open |
| Security controls | Information disclosure of auth state | generic client-facing error mapping | timing side-channel risk | accepted |
| Security controls | DoS through brute force | rate limiting controls | distributed attacks may exceed local limits | mitigated |
| Security controls | Privilege escalation from token scopes | explicit operation mapping | bad role mapping policy | open |
| Observability | Spoofing of telemetry source | context-bound logger fields | forged upstream headers in HTTP mode | open |
| Observability | Tampering with audit chain | HMAC chain design and append-only semantics | key compromise breaks trust | open |
| Observability | Repudiation without immutable storage | chained records and timestamping | storage backend immutability not guaranteed | open |
| Observability | Info disclosure via telemetry | redaction pipeline | custom fields could leak secrets | mitigated |
| Observability | DoS from high-cardinality metrics | bounded labels in instrumentation | accidental label explosion | open |
| Observability | Elevation through telemetry control plane | no privileged control APIs exposed | operational misconfiguration | accepted |
| Release pipeline | Spoofing release identity | GitHub OIDC + cosign keyless signing | compromised GitHub org admin | open |
| Release pipeline | Tampering release artifacts | checksums + cosign signatures | mirror tampering if verification skipped | mitigated |
| Release pipeline | Repudiation of release provenance | signed bundles in attestations directory | missing long-term archival | open |
| Release pipeline | Info disclosure in SBOM | SBOM excludes secrets and only lists dependencies | internal package names can reveal architecture | accepted |
| Release pipeline | DoS by dependency CVEs | pip-audit strict gate and lockfile | zero-day window remains | open |
| Release pipeline | Elevation through build runner abuse | least permissions in workflow and no shell in runtime image | runner compromise risk | accepted |

## Residual risk register

- Open risks require maintainer review every release.
- Accepted risks are documented with clear boundary assumptions.
- Mitigated risks remain covered by automated gates and release checklist.

## Controls mapping

- OWASP A06: SBOM + lockfile + vulnerability scanning
- OWASP A08: signed artifacts and provenance through OIDC
- OWASP A10: release script hard-fails on any gate failure
- NIST CM-7: least functionality in runtime image
- NIST SR-4: integrity verification instructions in release checklist
