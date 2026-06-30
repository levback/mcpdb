from __future__ import annotations

from mcpdb.security.ratelimit import RateLimiter


def test_ratelimit_bucket_emits_429_after_quota() -> None:
    limiter = RateLimiter(limit_per_minute=2)

    first = limiter.check("token-a", now_seconds=0.0)
    second = limiter.check("token-a", now_seconds=0.0)
    third = limiter.check("token-a", now_seconds=0.0)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds >= 1


def test_ratelimit_exempt_service_token_unlimited() -> None:
    limiter = RateLimiter(limit_per_minute=1, service_tokens={"svc-token"})

    first = limiter.check("svc-token", now_seconds=0.0)
    second = limiter.check("svc-token", now_seconds=0.0)
    third = limiter.check("svc-token", now_seconds=0.0)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is True


def test_ratelimit_headers_include_retry_after_on_denial() -> None:
    limiter = RateLimiter(limit_per_minute=1)

    limiter.check("token-a", now_seconds=0.0)
    denied = limiter.check("token-a", now_seconds=0.0)
    headers = RateLimiter.headers(denied)

    assert denied.allowed is False
    assert headers["X-RateLimit-Limit"] == "1"
    assert headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in headers


def test_ratelimit_prunes_stale_buckets() -> None:
    limiter = RateLimiter(limit_per_minute=1)

    limiter.check("token-old", now_seconds=0.0)
    limiter.check("token-new", now_seconds=601.0)

    assert "token-old" not in limiter._buckets
    assert "token-new" in limiter._buckets
