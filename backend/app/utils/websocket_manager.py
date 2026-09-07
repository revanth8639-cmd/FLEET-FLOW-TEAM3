"""Redis-backed fan-out for live GPS WebSocket clients."""
from __future__ import annotations

import asyncio
import json
import os
import time

import redis.asyncio as redis
from fastapi import WebSocket


class GPSConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._redis = None
        self._listener: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._last_seen: dict[WebSocket, float] = {}
        self.channel = "fleetflow:gps"

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        self._last_seen[websocket] = time.monotonic()

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        self._last_seen.pop(websocket, None)

    def touch(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._last_seen[websocket] = time.monotonic()

    async def broadcast(self, event: dict) -> None:
        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(event)
            except Exception:
                self.disconnect(websocket)

    async def start(self) -> None:
        if self._listener or self._heartbeat_task:
            return
        try:
            self._redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
            await self._redis.ping()
            self._listener = asyncio.create_task(self._listen())
        except Exception:
            self._redis = None
        self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def stop(self) -> None:
        if self._listener:
            self._listener.cancel()
            try:
                await self._listener
            except asyncio.CancelledError:
                pass
            self._listener = None
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def publish(self, event: dict) -> None:
        if self._redis:
            try:
                await self._redis.publish(self.channel, json.dumps(event))
                return
            except Exception:
                self._redis = None
        await self.broadcast(event)

    async def _listen(self) -> None:
        assert self._redis is not None
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self.broadcast(json.loads(message["data"]))
        finally:
            await pubsub.unsubscribe(self.channel)
            await pubsub.aclose()

    async def _heartbeat(self) -> None:
        """Ping clients and clean connections that stop responding."""
        while True:
            await asyncio.sleep(30)
            cutoff = time.monotonic() - 90
            for websocket in tuple(self._connections):
                if self._last_seen.get(websocket, 0) < cutoff:
                    self.disconnect(websocket)
                    continue
                try:
                    await websocket.send_json({"type": "server_ping"})
                except Exception:
                    self.disconnect(websocket)


gps_connections = GPSConnectionManager()
