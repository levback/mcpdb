# Security Model

This document maps implementation behavior to OWASP Top 10 2021 and NIST SP 800-53 moderate controls.

| Control | Implementation |
|---|---|
| OWASP A01 Broken Access Control | Policy default deny by Operation Class; explicit allow-lists |
| OWASP A02 Cryptographic Failures | TLS for HTTP deployments; secrets never logged |
| OWASP A03 Injection | SQL parameter binding only; Mongo operator allow-list |
| OWASP A04 Insecure Design | Typed Context + Policy at Tool boundaries |
| OWASP A05 Misconfiguration | Safe defaults, loud warnings for unsafe combinations |
| OWASP A06 Vulnerable Components | lockfile committed; audit scans in scripts |
| OWASP A07 Auth Failures | bearer token validation with issuer/audience checks |
| OWASP A08 Integrity Failures | pre-commit lock checks and reproducible env setup |
| OWASP A09 Logging Failures | structured audit for authz and Tool invocation |
| OWASP A10 SSRF | URL allow-list and resolution checks in config policies |
| NIST AU-2/AU-3 | who/when/source/action/target/outcome audit fields |
| NIST SA-5 | docs and behavior verified together in tests |

## Unsafe deployment combinations

The following is unsafe and must not be used in production:

- `bind_host=0.0.0.0`
- `auth_enabled=false`

This combination permits unauthenticated network access. # OWASP A05

## Read-only default

Mode defaults to `read_only`. Enabling writes requires explicit configuration and policy alignment.
