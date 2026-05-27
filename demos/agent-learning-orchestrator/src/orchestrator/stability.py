"""Top-gene stability comparison between internal cycles."""
from __future__ import annotations

from typing import Iterable


def jaccard_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    a = {gene for gene in left if gene}
    b = {gene for gene in right if gene}
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


def compare_top_genes(
    previous: list[str],
    current: list[str],
    *,
    top_n: int = 10,
    stable_threshold: float = 0.5,
) -> dict:
    prev = previous[:top_n]
    curr = current[:top_n]
    score = jaccard_similarity(prev, curr)
    return {
        "top_n": top_n,
        "previous_genes": prev,
        "current_genes": curr,
        "jaccard": round(score, 4),
        "stable": score >= stable_threshold,
        "overlap_count": len(set(prev) & set(curr)),
    }
