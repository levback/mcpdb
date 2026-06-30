filepath: phases/12-release-and-hardening.md
# Phase 12 — Release & Hardening (SBOM, Sigstore, Threat Model Sign-off)

> **Pre-reqs:** phase 11 merged.

## §1. Objective
Ship the first stable release with reproducible builds, signed artifacts, SBOM, and a signed threat-model document. CI produces a SLSA Level 3 provenance.

## §2. SCOPE BOUNDARY
In scope:
- `uv build` configured; wheel + sdist.
- CycloneDX SBOM emitted at build, attached to release.
- Sigstore `cosign sign-blob` of wheel, sdist, SBOM, and checksums.
- `Dockerfile` hardened runtime (distroless, read-only FS, non-root, drop capabilities).
- `docker-compose.prod.yml` production reference.
- `THREAT_MODEL.md` covers STRIDE per component, signed off by maintainers.
- Supply-chain: Renovate, Dependabot OR manual weekly review; `pip-audit` in CI gate.

Out of scope:
- PyPI token rotation policy (org-level).
- Public marketing site.

## §3. Reference
DIRECTIVE.md §2 (uv, docker). OWASP A06, A08, A10 (release-time). NIST SP 800-53 CM-2, CM-7, SA-12, SA-15, SR-3, SR-4. SLSA v1.0 L3.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `pyproject.toml` | `[build-system]`, `[project]` finalized | +40 |
| `scripts/release.sh` | full release pipeline | 120 |
| `scripts/sign.sh` | cosign wrapper | 40 |
| `Dockerfile` | hardened runtime | +20 over phase 01 |
| `docker-compose.prod.yml` | production reference | 80 |
| `.github/workflows/release.yml` | tag-triggered release job | 80 |
| `docs/security/THREAT_MODEL.md` | STRIDE per component | 400 |
| `docs/security/RELEASE_CHECKLIST.md` | pre-release gate | 80 |
| `sbom/` | generated at release | generated |
| `attestations/` | sigstore bundles | generated |
| `tests/release/test_sbom_valid.py` | CycloneDX 1.5 schema | 60 |
| `tests/release/test_signatures_valid.py` | cosign verify-blob | 60 |
| `tests/release/test_dockerfile_hardening.py` | uses `dive`, `hadolint` | 80 |

## §5. Functional Requirements
1. `scripts/release.sh vX.Y.Z` runs: lint, type, tests, audit, SBOM build, cosign sign, tag, upload draft.
2. SBOM is CycloneDX 1.5 JSON, includes all transitive deps.
3. All artifacts (wheel, sdist, SBOM, checksums.txt) signed with cosign keyless via OIDC.
4. Docker image uses `gcr.io/distroless/static-debian12:nonroot`, `USER 65532:65532`, `READONLY` root FS, drop ALL caps.
5. `pip-audit` finds zero high/critical vulnerabilities on the locked set.
6. `THREAT_MODEL.md` lists threats per STRIDE, mitigation, residual risk, status (open/mitigated/accepted).

## §6. Test Plan
- `test_sbom_matches_cyclonedx_1_5_schema`
- `test_sbom_includes_all_top_level_packages`
- `test_signature_verifies_against_signer_identity`
- `test_signature_rejects_tampered_blob`
- `test_dockerfile_no_shell_in_runtime`
- `test_dockerfile_user_is_non_root`
- `test_dockerfile_no_capabilities_added`
- `test_pip_audit_clean_on_lockfile`
- `test_threat_model_lists_each_component`
- `test_threat_model_residual_risk_field_present`

## §7. Security Requirements
- A06: SBOM emitted, pinned deps; Renovate auto-merge only for patch updates after CI green.
- A08: build provenance via GitHub OIDC; signatures verify on `cosign verify`.
- A10: release script refuses to publish if any gate fails.
- NIST CM-7: least-functionality defaults in production image.
- NIST SR-4: provenance + integrity verification documented.

## §8. DoD
- [ ] Dry-run release on a fork produces all artifacts and signatures.
- [ ] `cosign verify-blob` succeeds for every artifact.
- [ ] Threat model reviewed + signed off by at least one additional maintainer.
- [ ] `pip-audit --strict` returns clean.

## §9. Anti-Patterns
- No `--no-verify` flags in release path.
- No `:latest` Docker tags for release builds (immutable tags only).
- No uploading without `cosign sign` and `--attachment sbom`.
