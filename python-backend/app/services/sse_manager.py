from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sse_starlette.event import JSONServerSentEvent


class SSEManagerError(RuntimeError):
    """Raised when an SSE stream cannot be resolved safely."""


@dataclass(slots=True)
class _ManagedStream:
    queue: asyncio.Queue[JSONServerSentEvent | object]
    closed: bool = False
    disconnect_task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    producer_task: asyncio.Task[None] | None = None


_STREAM_END = object()
_RECONNECT_GRACE_SECONDS = 8.0


class SSEManager:
    def __init__(self) -> None:
        self._project_streams: dict[str, dict[str, _ManagedStream]] = {}
        self._lock = asyncio.Lock()

    async def open_stream(self, project_id: str) -> tuple[str, AsyncGenerator[JSONServerSentEvent, None]]:
        stream_id = self._create_stream_id()
        stream = await self.create_stream(project_id, stream_id=stream_id)
        return stream_id, stream

    async def create_stream(
        self,
        project_id: str,
        *,
        stream_id: str | None = None,
    ) -> AsyncGenerator[JSONServerSentEvent, None]:
        resolved_stream_id = stream_id or self._create_stream_id()

        async with self._lock:
            project_streams = self._project_streams.setdefault(project_id, {})
            managed_stream = project_streams.get(resolved_stream_id)
            if managed_stream is None:
                managed_stream = _ManagedStream(queue=asyncio.Queue())
                project_streams[resolved_stream_id] = managed_stream
            else:
                self._cancel_disconnect_task(managed_stream)

        async def event_stream() -> AsyncGenerator[JSONServerSentEvent, None]:
            while True:
                queued_event = await managed_stream.queue.get()
                if queued_event is _STREAM_END:
                    break

                yield queued_event

        return event_stream()

    async def send_event(
        self,
        project_id: str,
        event: str,
        data: dict[str, Any],
        *,
        stream_id: str | None = None,
    ) -> None:
        stream = await self._get_stream(project_id, stream_id=stream_id)
        if stream is None:
            return

        async with stream.lock:
            if stream.closed:
                return

            await stream.queue.put(JSONServerSentEvent(data=data, event=event))

        if event == "done":
            await self.close_stream(project_id, stream_id=stream_id)

    async def close_stream(self, project_id: str, *, stream_id: str | None = None) -> None:
        streams = await self._take_streams_for_close(project_id, stream_id=stream_id)

        for managed_stream in streams:
            self._cancel_disconnect_task(managed_stream)
            async with managed_stream.lock:
                if managed_stream.closed:
                    continue

                managed_stream.closed = True
                await managed_stream.queue.put(_STREAM_END)

    async def has_stream(self, project_id: str, *, stream_id: str) -> bool:
        async with self._lock:
            return stream_id in self._project_streams.get(project_id, {})

    async def register_producer_task(
        self,
        project_id: str,
        *,
        stream_id: str,
        producer_task: asyncio.Task[None],
    ) -> None:
        stream = await self._get_stream(project_id, stream_id=stream_id)
        if stream is None:
            return
        stream.producer_task = producer_task

    async def mark_client_disconnected(self, project_id: str, *, stream_id: str) -> None:
        stream = await self._get_stream(project_id, stream_id=stream_id)
        if stream is None or stream.closed:
            return

        async def _disconnect_later() -> None:
            try:
                await asyncio.sleep(_RECONNECT_GRACE_SECONDS)
                producer_task = stream.producer_task
                if producer_task is not None and not producer_task.done():
                    producer_task.cancel()
                await self.close_stream(project_id, stream_id=stream_id)
            except asyncio.CancelledError:
                return

        stream.disconnect_task = asyncio.create_task(_disconnect_later())

    async def cancel_stream(self, project_id: str, *, stream_id: str) -> None:
        stream = await self._get_stream(project_id, stream_id=stream_id)
        if stream is None:
            return

        producer_task = stream.producer_task
        if producer_task is not None and not producer_task.done():
            producer_task.cancel()
        await self.close_stream(project_id, stream_id=stream_id)

    async def shutdown(self) -> None:
        async with self._lock:
            project_ids = list(self._project_streams.keys())

        for project_id in project_ids:
            await self.close_stream(project_id)

    async def _get_stream(self, project_id: str, *, stream_id: str | None = None) -> _ManagedStream | None:
        async with self._lock:
            project_streams = self._project_streams.get(project_id, {})

            if stream_id is not None:
                return project_streams.get(stream_id)

            if not project_streams:
                return None

            if len(project_streams) > 1:
                raise SSEManagerError(
                    f"Multiple active SSE streams exist for project '{project_id}'. Provide a stream_id.",
                )

            return next(iter(project_streams.values()))

    async def _take_streams_for_close(
        self,
        project_id: str,
        *,
        stream_id: str | None = None,
    ) -> list[_ManagedStream]:
        async with self._lock:
            project_streams = self._project_streams.get(project_id)
            if not project_streams:
                return []

            if stream_id is not None:
                managed_stream = project_streams.pop(stream_id, None)
                if not project_streams:
                    self._project_streams.pop(project_id, None)
                return [managed_stream] if managed_stream is not None else []

            streams = list(project_streams.values())
            self._project_streams.pop(project_id, None)
            return streams

    async def _discard_stream(self, project_id: str, stream_id: str) -> None:
        async with self._lock:
            project_streams = self._project_streams.get(project_id)
            if not project_streams:
                return

            project_streams.pop(stream_id, None)
            if not project_streams:
                self._project_streams.pop(project_id, None)

    def _create_stream_id(self) -> str:
        return uuid4().hex

    def _cancel_disconnect_task(self, stream: _ManagedStream) -> None:
        disconnect_task = stream.disconnect_task
        if disconnect_task is None:
            return

        disconnect_task.cancel()
        stream.disconnect_task = None
