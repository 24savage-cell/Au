"""
速率限制器模块

提供基于滑动窗口的速率限制功能
"""

import time
from collections import deque
from typing import Optional


class RateLimiter:
    """
    滑动窗口速率限制器

    Args:
        max_requests: 窗口内最大请求数
        window_seconds: 窗口时间(秒)
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: deque[float] = deque()

    def allow(self) -> bool:
        """检查是否允许请求"""
        now = time.time()
        self._cleanup(now)
        if len(self._requests) >= self._max_requests:
            return False
        self._requests.append(now)
        return True

    def _cleanup(self, now: float) -> None:
        """清理过期记录"""
        cutoff = now - self._window_seconds
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    @property
    def remaining(self) -> int:
        """剩余可用请求数"""
        self._cleanup(time.time())
        return max(0, self._max_requests - len(self._requests))
