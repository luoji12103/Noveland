from __future__ import annotations

import asyncio
import contextlib
import inspect
import threading
from collections.abc import Awaitable, Callable, Generator
from concurrent.futures import Future
from typing import Any, TypeVar, cast

import anyio.from_thread
import pytest
import starlette.testclient

T = TypeVar("T")


class _AsyncioWakeupPortal:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def call(self, func: Callable[..., T], *args: object) -> T:
        async def runner() -> T:
            result = func(*args)
            if inspect.isawaitable(result):
                return await cast(Awaitable[T], result)
            return result

        return asyncio.run_coroutine_threadsafe(runner(), self._loop).result()

    def start_task_soon(
        self,
        func: Callable[..., Any],
        *args: object,
        name: object = None,
    ) -> Future[Any]:
        return self._submit_task(func, args, {}, name)

    def start_task(
        self,
        func: Callable[..., Any],
        *args: object,
        name: object = None,
    ) -> tuple[Future[Any], Any]:
        started: Future[Any] = Future()

        class TaskStatus:
            def started(self, value: object = None) -> None:
                if not started.done():
                    started.set_result(value)

        task_future = self._submit_task(func, args, {"task_status": TaskStatus()}, name)
        return task_future, started.result()

    def stop(self, cancel_remaining_tasks: bool = False) -> None:
        async def shutdown() -> None:
            if cancel_remaining_tasks:
                current = asyncio.current_task()
                tasks = [
                    task
                    for task in asyncio.all_tasks(self._loop)
                    if task is not current and not task.done()
                ]
                for task in tasks:
                    task.cancel()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            self._loop.call_soon(self._loop.stop)

        asyncio.create_task(shutdown())

    def _submit_task(
        self,
        func: Callable[..., Any],
        args: tuple[object, ...],
        kwargs: dict[str, object],
        name: object,
    ) -> Future[Any]:
        async def runner() -> Any:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        return asyncio.run_coroutine_threadsafe(runner(), self._loop)


@contextlib.contextmanager
def _start_wakeup_blocking_portal(
    backend: str = "asyncio",
    backend_options: dict[str, Any] | None = None,
    *,
    name: str | None = None,
) -> Generator[Any, None, None]:
    del backend_options
    if backend != "asyncio":
        with _ORIGINAL_START_BLOCKING_PORTAL(backend=backend, name=name) as original_portal:
            yield original_portal
        return

    ready: Future[_AsyncioWakeupPortal] = Future()

    def run_loop() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        portal = _AsyncioWakeupPortal(loop)

        def wakeup_tick() -> None:
            if loop.is_running():
                loop.call_later(0.01, wakeup_tick)

        loop.call_soon(wakeup_tick)
        ready.set_result(portal)
        try:
            loop.run_forever()
        finally:
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    thread = threading.Thread(target=run_loop, daemon=True, name=name or "asyncio-test-portal")
    thread.start()
    portal = ready.result()
    try:
        yield portal
    finally:
        portal.call(portal.stop, True)
        thread.join(timeout=5)


_ORIGINAL_START_BLOCKING_PORTAL = anyio.from_thread.start_blocking_portal


@pytest.fixture(autouse=True)
def patch_testclient_blocking_portal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anyio.from_thread, "start_blocking_portal", _start_wakeup_blocking_portal)
    starlette_anyio = cast(Any, starlette.testclient).anyio
    monkeypatch.setattr(
        starlette_anyio.from_thread,
        "start_blocking_portal",
        _start_wakeup_blocking_portal,
    )
