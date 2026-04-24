from __future__ import annotations

from collections.abc import Callable, Sequence

from noveland.memory.contracts import (
    MemoryEvalCase,
    MemoryEvalCaseResult,
    MemoryEvalResult,
    MemorySearchRequest,
    MemorySearchResult,
)


def run_memory_eval_cases(
    *,
    backend: str,
    cases: Sequence[MemoryEvalCase],
    search_fn: Callable[[MemorySearchRequest], MemorySearchResult],
) -> MemoryEvalResult:
    results: list[MemoryEvalCaseResult] = []
    total_latency = 0
    latency_count = 0
    total_context_items = 0
    hit_case_count = 0

    for case in cases:
        search_result = search_fn(
            MemorySearchRequest(
                world_id=case.world_id,
                agent_id=case.agent_id,
                query_text=case.query_text,
                limit=case.limit,
            )
        )
        context_item_count = len(search_result.items)
        if context_item_count > 0:
            hit_case_count += 1
        if search_result.latency_ms is not None:
            total_latency += search_result.latency_ms
            latency_count += 1
        total_context_items += context_item_count
        results.append(
            MemoryEvalCaseResult(
                label=case.label,
                query_text=case.query_text,
                backend=search_result.backend,
                hit_count=context_item_count,
                context_item_count=context_item_count,
                latency_ms=search_result.latency_ms,
            )
        )

    average_latency_ms = None if latency_count == 0 else total_latency // latency_count
    average_context_items = 0.0 if not results else total_context_items / len(results)
    return MemoryEvalResult(
        backend=backend,
        case_count=len(results),
        hit_case_count=hit_case_count,
        average_latency_ms=average_latency_ms,
        average_context_items=average_context_items,
        cases=results,
    )
