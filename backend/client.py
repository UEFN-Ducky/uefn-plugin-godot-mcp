"""In-process MCP client for the Godot editor addon (streamable HTTP, bearer token).

The plugin owns the connection, so Godot shows up as one Store plugin instead of a
nested ``mcp.json`` server row.
"""

from __future__ import annotations

import asyncio
import base64
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from .constants import CALL_TIMEOUT_S, CONNECT_TIMEOUT_S

_TOTAL_TIMEOUT_S = CONNECT_TIMEOUT_S + CALL_TIMEOUT_S


class GodotMcpError(RuntimeError):
    """Readable failure talking to the Godot editor addon."""


def describe_error(exc: BaseException) -> str:
    """Flatten anyio task groups — their default text says nothing useful."""
    nested = getattr(exc, "exceptions", None)
    if nested:
        return "; ".join(describe_error(sub) for sub in nested)
    text = str(exc).strip()
    if "401" in text:
        return "editor refused the token (401): restart it with godot_launch_editor"
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def list_tools(url: str, token: str) -> list[dict[str, Any]]:
    """Live editor tools with their input schemas."""

    async def run(session: Any) -> list[dict[str, Any]]:
        result = await asyncio.wait_for(session.list_tools(), timeout=CALL_TIMEOUT_S)
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {},
            }
            for tool in (result.tools or [])
        ]

    return _with_session(url, token, run)


def call_tool(
    url: str, token: str, name: str, arguments: dict[str, Any] | None = None, *, media_dir: Path | None = None
) -> dict[str, Any]:
    """Invoke one editor tool; text is flattened, pictures are saved as files."""

    async def run(session: Any) -> dict[str, Any]:
        result = await asyncio.wait_for(session.call_tool(name, arguments or {}), timeout=CALL_TIMEOUT_S)
        text, images = flatten_content(getattr(result, "content", None), media_dir)
        out: dict[str, Any] = {
            "ok": not bool(getattr(result, "isError", False)),
            "tool": name,
            "text": text,
        }
        structured = getattr(result, "structuredContent", None)
        if structured:
            out["structured"] = structured
        if images:
            out["images"] = images
        return out

    return _with_session(url, token, run)


def flatten_content(content: Any, media_dir: Path | None = None) -> tuple[str, list[str]]:
    parts: list[str] = []
    images: list[str] = []
    for i, block in enumerate(content or []):
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
            continue
        data = getattr(block, "data", None)
        mime = str(getattr(block, "mimeType", "") or "")
        if isinstance(data, str) and mime.startswith("image/") and media_dir is not None:
            media_dir.mkdir(parents=True, exist_ok=True)
            ext = mime.split("/", 1)[1].split("+", 1)[0] or "png"
            path = media_dir / f"godot_{int(time.time() * 1000)}_{i}.{ext}"
            path.write_bytes(base64.b64decode(data))
            images.append(str(path))
            continue
        kind = str(getattr(block, "type", "") or type(block).__name__)
        parts.append(f"[{kind}]")
    return "\n".join(parts), images


async def _session_scope(url: str, token: str, run: Callable[[Any], Awaitable[Any]]) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {token}"} if token else None
    # Editor work can run long; keep the HTTP read window above CALL_TIMEOUT_S.
    async with streamablehttp_client(url, headers=headers, timeout=CALL_TIMEOUT_S) as transport:
        read, write = transport[0], transport[1]
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=CONNECT_TIMEOUT_S)
            return await run(session)


def _with_session(url: str, token: str, run: Callable[[Any], Awaitable[Any]]) -> Any:
    try:
        return run_isolated(lambda: _session_scope(url, token, run), timeout=_TOTAL_TIMEOUT_S)
    except Exception as exc:
        raise GodotMcpError(f"{describe_error(exc)} ({url})") from exc


def run_isolated(factory: Callable[[], Awaitable[Any]], *, timeout: float) -> Any:
    """Run one coroutine on a private loop — tool calls arrive on many threads."""
    box: dict[str, Any] = {}

    def target() -> None:
        try:
            box["value"] = asyncio.run(factory())
        except BaseException as exc:  # noqa: BLE001 - re-raised to the caller
            box["error"] = exc

    thread = threading.Thread(target=target, daemon=True, name="godot-mcp-call")
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"Godot editor did not answer within {timeout:.0f}s")
    error = box.get("error")
    if error is not None:
        raise error
    return box.get("value")
