"""Utilities for managing concurrency limits for CPU-bound tasks."""

from __future__ import annotations

import os
from functools import lru_cache

from anyio import CapacityLimiter

from app.core.config import settings

DEFAULT_TOKEN_COUNT = max(1, os.cpu_count() or 1)


@lru_cache(maxsize=1)
def get_pdf_merge_limiter() -> CapacityLimiter:
    """Return a shared limiter for CPU bound PDF merge operations."""

    configured_limit = settings.pdf_merge_max_parallel
    if configured_limit is None:
        return CapacityLimiter(DEFAULT_TOKEN_COUNT)

    return CapacityLimiter(max(1, configured_limit))

