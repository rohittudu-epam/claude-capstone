"""Deterministic keyword similarity between two notes.

Method (documented so suggestions are explainable and reproducible):
1. Keywords are lowercase letter/digit runs of at least 3 characters, excluding English stopwords and
   pure numbers. There is no stemming, so "deployment" and "deployments" are different keywords.
2. A keyword weighs 3 if it appears in the note's title, otherwise 1 (only the first 20,000 body
   characters are read).
3. The score is the weighted Jaccard index of the two weight maps:
       sum(min(wa, wb) over shared keywords) / sum(max(wa, wb) over all keywords)
   so it is 0 for no overlap and 1 for identical keyword sets, whatever the order or the note sizes.
Ties and display order always break alphabetically, never by hash or insertion order.
"""

import re
from dataclasses import dataclass

TITLE_WEIGHT = 3
BODY_CHARS = 20_000
MIN_TOKEN_LENGTH = 3
MAX_EXPLAINED_KEYWORDS = 8

_TOKEN = re.compile(r"[^\W_]+")

STOPWORDS = frozenset(
    """
    about above after again all also and any are because been before being below between both but can could did
    does doing down during each few for from further had has have having her here hers him his how into its itself
    just more most multiple not now off once only other our ours out over own same she should some such than that
    the their theirs them then there these they this those through too under until upon very was were what when
    where which while who whom why will with would you your yours
    """.split()
)


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN.findall(text.lower())
        if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS and not token.isdigit()
    ]


def keyword_weights(title: str, body: str) -> dict[str, int]:
    weights = dict.fromkeys(tokenize(body[:BODY_CHARS]), 1)
    weights.update(dict.fromkeys(tokenize(title), TITLE_WEIGHT))
    return weights


@dataclass(frozen=True)
class Similarity:
    score: float
    shared: tuple[str, ...]


def similarity(a: dict[str, int], b: dict[str, int]) -> Similarity:
    shared = a.keys() & b.keys()
    if not shared:
        return Similarity(0.0, ())
    intersection = sum(min(a[k], b[k]) for k in shared)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in a.keys() | b.keys())
    ordered = tuple(sorted(shared, key=lambda k: (-min(a[k], b[k]), k)))
    return Similarity(round(intersection / union, 4), ordered)


def explain(result: Similarity) -> str:
    shown = ", ".join(result.shared[:MAX_EXPLAINED_KEYWORDS])
    more = len(result.shared) - MAX_EXPLAINED_KEYWORDS
    suffix = f" and {more} more" if more > 0 else ""
    return f"Shared keywords: {shown}{suffix} ({result.score:.0%} keyword overlap)"
