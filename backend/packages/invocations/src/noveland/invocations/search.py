from __future__ import annotations

from noveland.invocations.contracts import InvocationTagFilter


def parse_tag_filters(encoded_filters: list[str]) -> list[InvocationTagFilter]:
    return [InvocationTagFilter.parse(encoded) for encoded in encoded_filters]
