from __future__ import annotations

import asyncio

from app.services.sse_manager import SSEManager


def test_sse_manager_stream_receives_events_and_closes() -> None:
    asyncio.run(_run_sse_manager_test())


async def _run_sse_manager_test() -> None:
    sse_manager = SSEManager()
    stream = await sse_manager.create_stream("project-1")

    await sse_manager.send_event("project-1", "thinking", {"content": "hello"})

    event = await asyncio.wait_for(anext(stream), timeout=1)
    encoded_event = event.encode().decode("utf-8")

    assert "event: thinking" in encoded_event
    assert 'data: {"content":"hello"}' in encoded_event

    await sse_manager.close_stream("project-1")

    try:
        await asyncio.wait_for(anext(stream), timeout=1)
    except StopAsyncIteration:
        return

    raise AssertionError("SSE stream should have been closed.")
