"""Links and suggestions are stored once per unordered note pair, with the smaller id first."""

from uuid import UUID


def canonical_pair(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    if a == b:
        raise ValueError("a note cannot be linked to itself")
    return (a, b) if a < b else (b, a)
