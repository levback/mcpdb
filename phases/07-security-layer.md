filepath: phases/07-security-layer.md
# Phase 07 — Security Layer (Authn, Authz, Rate Limit, Audit)

> **Pre-reqs:** phase 06 merged.

## §1. Objective
Add production-grade security: OAuth 2.1 bearer token validation for HTTP, HMAC-chained audit log, token-bucket rate limiting, and a deny-by-default policy engine driven by an external policy file.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/security/auth.py` — JWT validation (HS256, RS256, ES256), clock skew ±60s, audience/issuer checks.
- `src/mcpdb/security/authz.py` — Casbin-style policy file with `subject, action, resource` rules.
- `src/mcpdb/security/ratelimit.py` — `slowapi` integration, per-token bucket.
- `src/mcpdb/security/audit.py` — HMAC-chained JSONL sink, pluggable via `AuditSink` ABC.
- `src/mcpdb/security/secrets.py` — concrete `VaultProvider` implementations (env, file, AWS SM stub).

Out of scope:
- CLI hardening (phase 08), observability (phase 09).

## §3. Reference
DIRECTIVE.md §2 (pyjwt, slowapi), §5 A01/A02/A07/A09. NIST SP 800-53 AC-3, AU-2, AU-3, AU-9, IA-2, IA-5, SC-8.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/security/__init__.py` | exports | 15 |
| `src/mcpdb/security/auth.py` | `verify_bearer(token, settings) -> Principal` | 180 |
| `src/mcpdb/security/authz.py` | policy file loader, enforcer, default-deny | 150 |
| `src/mcpdb/security/ratelimit.py` | `RateLimiter`, headers, exemptions | 90 |
| `src/mcpdb/security/audit.py` | `AuditSink` ABC, `HMACChainSink`, `CompositeSink` | 180 |
| `src/mcpdb/security/secrets.py` | `EnvVault`, `FileVault`, `AwsSmVault` stub | 140 |
| `tests/unit/security/test_auth.py` | JWT happy/exp/skew/aud/iss/alg=none | 250 |
| `tests/unit/security/test_authz.py` | matrix of (sub, action, resource) | 200 |
| `tests/unit/security/test_ratelimit.py` | bucket math, exemption for service tokens | 120 |
| `tests/unit/security/test_audit_chain.py` | HMAC chain integrity, tamper detection | 160 |
| `tests/security/test_owasp_a01.py` | end-to-end authz bypass attempts | 180 |
| `tests/security/test_owasp_a02.py` | secret leakage in logs / errors | 120 |
| `tests/security/test_owasp_a07.py` | JWT alg confusion, kid traversal | 150 |
| `examples/policies/deny_all.yaml` | default-deny starter | 10 |
| `examples/policies/read_only_engineers.yaml` | least-privilege example | 20 |

## §5. Functional Requirements
1. `verify_bearer(token, settings)`:
   - Constant-time compare header.
   - Reject `alg=none`, `alg=HS256` mismatch when configured for RS, unknown `kid`.
   - Enforce `aud`, `iss`, `exp`, `nbf`, `iat` (±60s skew).
   - On success, return `Principal(sub, scopes, claims)`.
2. Authz policy YAML schema: `subjects`, `actions` (tool names), `resources` (profile globs), `effect: allow|deny`. Default deny.
3. Rate limit: `60` requests/minute per token, configurable; returns `429` + `Retry-After`.
4. Audit sink: each entry `{prev_hash, ts, who, source, action, target, outcome, request_id, meta}`. `next_hash = HMAC-SHA256(key, prev_hash||json(entry))`. Verification walks the chain.
5. Secret providers: `EnvVault` reads from env at resolve-time; `FileVault` reads a JSON file at resolve-time with `0600` check; `AwsSmVault` stubbed interface.

## §6. Test Plan
- `test_auth_jwt_happy_path`
- `test_auth_jwt_expired_rejected`
- `test_auth_jwt_clock_skew_within_60s_accepted`
- `test_auth_jwt_clock_skew_beyond_60s_rejected`
- `test_auth_jwt_audience_mismatch_rejected`
- `test_auth_jwt_issuer_mismatch_rejected`
- `test_auth_jwt_alg_none_rejected` — OWASP A07
- `test_auth_jwt_kid_traversal_rejected`
- `test_authz_default_deny`
- `test_authz_allow_overrides_deny_for_specific_subject`
- `test_authz_resource_glob_matches_profile`
- `test_authz_unknown_action_rejected`
- `test_ratelimit_bucket_emits_429_after_quota`
- `test_ratelimit_exempt_service_token_unlimited`
- `test_audit_chain_integrity_pass`
- `test_audit_chain_detects_tamper_of_any_field`
- `test_audit_chain_detects_reorder`
- `test_security_owasp_a01_try_bypass_with_extra_claim`
- `test_security_owasp_a02_secret_not_in_500_body`
- `test_security_owasp_a07_alg_confusion_attempt`

## §7. Security Requirements
- A01: all tools now require authn+authz; default deny.
- A02: secrets via providers only; never logged, never in 5xx bodies (whitelisted safe fields only).
- A07: algorithm pinned per settings; `kid` resolved via allow-list.
- A09: audit log durable, append-only; verifier exposed for compliance jobs.
- NIST SC-8: TLS termination documented; HSTS on by default.
- NIST SC-13: HMAC-SHA-256; rotate key via `key_id` indirection.
- NIST IA-5: tokens have `aud`, `iss`, scoped `sub`.

## §8. DoD
- [ ] All §4 tests pass; coverage ≥90% on `src/mcpdb/security/`.
- [ ] `examples/policies/deny_all.yaml` actually denies everything (test proves).
- [ ] Audit verifier CLI: `uv run mcpdb audit verify <file>` exits 0 on clean chain, 2 on tamper.

## §9. Anti-Patterns
- No JWT verification with `jwt.decode` without `algorithms=[...]`.
- No `casbin.Enforcer(...)` style global state — pass via DI.
- No audit log writes to a mutable file path derived from user input.
