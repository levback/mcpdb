from __future__ import annotations

import math
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    limit: int
    remaining: int


@dataclass
class TokenBucket:
    # Intentional mutability under RateLimiter lock for low-overhead refill accounting.
    limit_per_minute: int
    tokens: float
    last_refill: float

    def consume(self, now_seconds: float) -> RateLimitDecision:
        refill_rate_per_second = self.limit_per_minute / 60.0
        elapsed = max(now_seconds - self.last_refill, 0.0)
        self.tokens = min(self.limit_per_minute, self.tokens + elapsed * refill_rate_per_second)
        self.last_refill = now_seconds

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
                limit=self.limit_per_minute,
                remaining=max(int(self.tokens), 0),
            )

        retry_after = math.ceil((1.0 - self.tokens) / refill_rate_per_second)
        return RateLimitDecision(
            allowed=False,
            retry_after_seconds=max(retry_after, 1),
            limit=self.limit_per_minute,
            remaining=0,
        )


class RateLimiter:
    def __init__(self, limit_per_minute: int = 60, service_tokens: set[str] | None = None) -> None:
        self._limit_per_minute = limit_per_minute
        self._service_tokens = set(service_tokens or set())
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = Lock()
        self._stale_after_seconds = 10 * 60.0

    def check(self, token: str, now_seconds: float | None = None) -> RateLimitDecision:
        if token in self._service_tokens:
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
                limit=self._limit_per_minute,
                remaining=self._limit_per_minute,
            )

        current = time.monotonic() if now_seconds is None else now_seconds
        with self._lock:
            self._prune_stale_buckets(current)
            bucket = self._buckets.get(token)
            if bucket is None:
                bucket = TokenBucket(
                    limit_per_minute=self._limit_per_minute,
                    tokens=float(self._limit_per_minute),
                    last_refill=current,
                )
                self._buckets[token] = bucket
            return bucket.consume(current)

    def _prune_stale_buckets(self, now_seconds: float) -> None:
        stale_tokens = [
            token
            for token, bucket in self._buckets.items()
            if now_seconds - bucket.last_refill > self._stale_after_seconds
        ]
        for token in stale_tokens:
            self._buckets.pop(token, None)

    @staticmethod
    def headers(decision: RateLimitDecision) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
        }
        if not decision.allowed:
            headers["Retry-After"] = str(decision.retry_after_seconds)
        return headers


def build_slowapi_limiter(default_limit: str = "60/minute") -> Any:
    from slowapi import Limiter

    return Limiter(
        key_func=lambda request: request.headers.get("Authorization", ""),
        default_limits=[default_limit],
    )
