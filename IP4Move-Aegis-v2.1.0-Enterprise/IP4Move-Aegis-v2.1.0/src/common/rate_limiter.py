"""Stub rate limiter used by the transport layer."""


class RateLimiter:
    """Minimal stub so transport.py can be imported in tests."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def allow(self, key: str = "") -> bool:
        return True
