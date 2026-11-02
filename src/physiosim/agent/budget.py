"""Portable cooperative deadlines; no process-global timers or signal handlers."""
import math
import time


class BudgetExceeded(Exception):
    """The session's cooperative wall-clock budget has expired."""


class Deadline:
    def __init__(self, seconds):
        if seconds is not None and (isinstance(seconds, bool) or not isinstance(seconds, (int, float))
                                    or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError('wall_clock_s must be positive and finite, or None')
        self.expires_at = None if seconds is None else time.monotonic() + seconds

    def remaining(self):
        if self.expires_at is None:
            return math.inf
        remaining = self.expires_at - time.monotonic()
        if remaining <= 0:
            raise BudgetExceeded('Session wall-clock budget exhausted.')
        return remaining

    def check(self):
        self.remaining()

    def timeout(self, configured):
        return min(configured, self.remaining())
