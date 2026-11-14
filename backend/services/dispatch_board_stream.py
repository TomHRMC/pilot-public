"""
Dispatch Board SSE Stream Service — B3/A19.

Manages per-tenant Redis Pub/Sub channels for real-time dispatch board updates.
This is the canonical SSE pattern — reused by B6, B8, B11.

Channel: dispatch:{tenant_id}
Replay:  dispatch_stream:{tenant_id}:events  (Redis list, max MAX_HISTORY_LEN items)
Event types (per mvp-arch.md §13.11):
  job_scheduled, job_rescheduled, job_reassigned, job_unassigned,
  conflict_detected, conflict_cleared, calendar_sync_status

SSE wire format per event:
  id: <event_id>\\n
  event: <event_type>\\n
  data: <json_payload>\\n\\n

Heartbeat: server comment line (: heartbeat) every HEARTBEAT_INTERVAL_SECONDS.
Idle timeout: IDLE_TIMEOUT_SECONDS of no data closes the connection.
Reconnect: Last-Event-ID header triggers replay from dispatch_stream history.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "dispatch"
EVENT_HISTORY_PREFIX = "dispatch_stream"
MAX_HISTORY_LEN = 100
HEARTBEAT_INTERVAL_SECONDS = 15
IDLE_TIMEOUT_SECONDS = 300


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _channel_name(tenant_id: str) -> str:
    """Return the Redis Pub/Sub channel name for a tenant.

    Args:
        tenant_id: UUID string of the tenant.
    Returns:
        str: e.g. 'dispatch:a1b2c3d4-...'
    """
    return f"{CHANNEL_PREFIX}:{tenant_id}"


def _history_key(tenant_id: str) -> str:
    """Return the Redis list key for event replay history.

    Args:
        tenant_id: UUID string of the tenant.
    Returns:
        str: e.g. 'dispatch_stream:a1b2c3d4-...:events'
    """
    return f"{EVENT_HISTORY_PREFIX}:{tenant_id}:events"


def _make_event_id() -> str:
    """Generate a monotonic event ID using unix timestamp + random suffix."""
    return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def _format_sse(
    event_type: str,
    payload: dict,
    event_id: str,
) -> str:
    """Format a dict as an SSE event string.

    Returns:
        str: e.g. 'id: 123\\nevent: job_rescheduled\\ndata: {...}\\n\\n'
    """
    data = json.dumps(payload)
    return f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"


# ---------------------------------------------------------------------------
# Public: broadcast
# ---------------------------------------------------------------------------


async def broadcast_board_event(
    redis_client,
    tenant_id: str,
    event_type: str,
    payload: dict,
    event_id: str | None = None,
) -> None:
    """Publish a board event to the tenant's SSE channel and append to replay history.

    Args:
        redis_client: Async Redis client (aioredis / redis.asyncio).
        tenant_id:    Tenant UUID string — enforces cross-tenant isolation.
        event_type:   One of: job_scheduled, job_rescheduled, job_reassigned,
                      job_unassigned, conflict_detected, conflict_cleared, calendar_sync_status.
        payload:      Event-specific dict (per §13.11 schema).
        event_id:     Optional string event ID for Last-Event-ID replay. Auto-generated if None.
    Returns:
        None
    Raises:
        redis.exceptions.RedisError: on connection failure (caller handles gracefully).
    """
    eid = event_id or _make_event_id()
    sse_str = _format_sse(event_type, payload, eid)

    channel = _channel_name(tenant_id)
    history = _history_key(tenant_id)

    # Store in replay history (LPUSH → trim to MAX_HISTORY_LEN)
    history_record = json.dumps(
        {
            "id": eid,
            "event_type": event_type,
            "payload": payload,
        }
    )
    await redis_client.lpush(history, history_record)
    await redis_client.ltrim(history, 0, MAX_HISTORY_LEN - 1)

    # Publish to Pub/Sub channel
    await redis_client.publish(channel, sse_str)
    logger.debug(
        "dispatch_board_stream.broadcast: tenant=%s event=%s id=%s",
        tenant_id,
        event_type,
        eid,
    )


# ---------------------------------------------------------------------------
# Public: SSE generator
# ---------------------------------------------------------------------------


async def sse_event_generator(
    redis_client,
    tenant_id: str,
    user_id: str,
    last_event_id: str | None = None,
) -> AsyncIterator[str]:
    """Async generator yielding SSE-formatted strings for a connected client.

    Replays missed events via last_event_id, then subscribes to live channel.
    Emits heartbeat comment lines every HEARTBEAT_INTERVAL_SECONDS.
    Raises asyncio.TimeoutError after IDLE_TIMEOUT_SECONDS with no data.

    Args:
        redis_client:  Async Redis client.
        tenant_id:     Tenant UUID string — SSE channel scoped to this tenant.
        user_id:       User UUID string — for audit/logging.
        last_event_id: If provided, replay all history events with ID > last_event_id.
    Yields:
        str: SSE-formatted event strings, e.g. 'event: job_rescheduled\\ndata: {...}\\nid: 42\\n\\n'
    """
    logger.info(
        "dispatch_board_stream.connect: tenant=%s user=%s last_event_id=%s",
        tenant_id,
        user_id,
        last_event_id,
    )

    # --- Replay missed events from history ---
    if last_event_id is not None:
        history_key = _history_key(tenant_id)
        try:
            # History is stored LIFO (newest first via LPUSH)
            history_raw = await redis_client.lrange(history_key, 0, MAX_HISTORY_LEN - 1)
            # Reverse to replay oldest-first
            replays = []
            for item in reversed(history_raw):
                record = json.loads(item)
                rec_id = record.get("id", "")
                # Replay events newer than last_event_id
                if rec_id > last_event_id:
                    replays.append(record)
            for record in replays:
                yield _format_sse(
                    record["event_type"],
                    record["payload"],
                    record["id"],
                )
        except Exception as exc:
            logger.warning("dispatch_board_stream.replay error: %s", exc)

    # --- Subscribe to live channel ---
    channel = _channel_name(tenant_id)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    last_activity = asyncio.get_event_loop().time()

    try:
        while True:
            now = asyncio.get_event_loop().time()

            # Idle timeout check
            if now - last_activity > IDLE_TIMEOUT_SECONDS:
                logger.info(
                    "dispatch_board_stream.idle_timeout: tenant=%s user=%s",
                    tenant_id,
                    user_id,
                )
                break

            # Poll for message with short timeout so we can send heartbeats
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=None),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except TimeoutError:
                # Send heartbeat comment
                yield ": heartbeat\n\n"
                continue

            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield data
                last_activity = asyncio.get_event_loop().time()
            else:
                # No real message — send heartbeat if due
                elapsed = asyncio.get_event_loop().time() - last_activity
                if elapsed >= HEARTBEAT_INTERVAL_SECONDS:
                    yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        logger.info(
            "dispatch_board_stream.disconnect: tenant=%s user=%s (client closed)",
            tenant_id,
            user_id,
        )
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
