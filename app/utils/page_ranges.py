import re
from typing import List

from fastapi import HTTPException

_range_token = re.compile(r"^\s*(\d+)\s*(-\s*(\d+)\s*)?$")


def parse_page_ranges(range_str: str, total_pages: int) -> List[int]:
    """Convert human friendly page ranges to zero-based indices."""

    indices: List[int] = []
    if not range_str.strip():
        return list(range(total_pages))

    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = _range_token.match(part)
        if not match:
            raise HTTPException(status_code=400, detail=f"Invalid range token: '{part}'")

        start = int(match.group(1))
        end = match.group(3)
        end_num = int(end) if end is not None else start

        if start < 1 or end_num < 1 or start > total_pages or end_num > total_pages:
            raise HTTPException(
                status_code=400,
                detail=f"Range out of bounds: '{part}' (doc has {total_pages} pages)",
            )

        if start <= end_num:
            rng = range(start - 1, end_num)
        else:
            rng = range(start - 1, end_num - 2, -1)

        indices.extend(list(rng))

    return indices
