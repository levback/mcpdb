# FAQ

## Why was my query denied?

The Policy decision likely denied the Operation Class, or a Cap was exceeded.

## Why do writes fail by default?

Mode defaults to `read_only` for production safety.

## Why do I get auth errors on HTTP transport?

Check issuer, audience, and token freshness in your auth configuration.

## Can I disable auth for testing?

Yes, but only on loopback development hosts. Never pair `auth_enabled=false` with `0.0.0.0`. # OWASP A05

## How do I inspect available resources?

Use `db_introspect` and resource URIs such as `db://<profile>/tables`.
