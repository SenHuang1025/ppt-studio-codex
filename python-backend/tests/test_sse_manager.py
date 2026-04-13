from __future__ import annotations

import asyncio

import pytest

from app.services.sse_manager import SSEManager


@pytest.mark.asyncio
async def test_sse_manager_stream_receives_events_and_closes() -> None:
    sse_manager = SSEManager()
    stream = await sse_manager.create_stream("project-1")

    await sse_manager.send_event("project-1", "thinking", {"content": "hello"})

    event = await asyncio.wait_for(anext(stream), timeout=1)
    encoded_event = event.encode().decode("utf-8")

    assert "event: thinking" in encoded_event
    assert 'data: {"content":"hello"}' in encoded_event

    await sse_manager.close_stream("project-1")

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(stream), timeout=1)
