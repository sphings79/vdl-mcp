# vdl-mcp — MCP server for vdl
# Copyright (C) 2026 sphings79
# SPDX-License-Identifier: AGPL-3.0-or-later
# Licensed under the GNU Affero General Public License v3.0 or later; see LICENSE.
"""Mock-based tests for the vdl-mcp tools (no live vdl needed)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from vdl_mcp import client, config, server

# The real AsyncClient — captured ONCE before any patching (client.httpx is the
# same module object, else a second _mock() would capture its own lambda).
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _mock() -> None:
    """Point the client's httpx at a fake vdl API."""
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p == "/api/resolve":
            return httpx.Response(200, json={"title": "My Video", "items": [
                {"id": "v1", "title": "Clip", "kind": "video", "duration": 42,
                 "variants": [{"label": "720p"}, {"label": "1080p"}, {"label": "720p"}]}]})
        if p == "/api/files":
            return httpx.Response(200, json={"files": [
                {"name": "youtube/clip.mp4", "basename": "clip.mp4", "folder": "youtube",
                 "size": 1000, "duration": 42, "labels": [{"text": "fun"}], "in_feed": False},
                {"name": "insta/reel.mp4", "basename": "reel.mp4", "folder": "insta",
                 "size": 500, "duration": 10, "labels": [], "in_feed": True}]})
        if p == "/api/download":
            return httpx.Response(200, json={"jobs": [{"id": "job1", "state": "queued"}]})
        if p == "/api/jobs/job1":
            return httpx.Response(200, json={"id": "job1", "state": "done", "filename": "clip.mp4", "error": None})
        if p.endswith("/transcribe"):
            return httpx.Response(200, json={"txt": "youtube/clip.txt"})
        if p == "/api/files/youtube/clip.txt":
            return httpx.Response(200, text="Hello world transcript.")
        if p == "/api/secret":
            return httpx.Response(401, text="unauthorized")
        return httpx.Response(404, text="nope")

    transport = httpx.MockTransport(handler)
    client.httpx.AsyncClient = lambda *a, **kw: _REAL_ASYNC_CLIENT(*a, **{**kw, "transport": transport})


def test_resolve_download_transcribe_chain():
    _mock()
    r = asyncio.run(server.resolve(url="http://x/v"))
    assert r["items"][0]["qualities"] == ["1080p", "720p"]  # deduped + sorted
    dl = asyncio.run(server.download(url="http://x/v", wait=True, timeout_seconds=20))
    assert dl["state"] == "done" and dl["name"] == "youtube/clip.mp4"  # rel name resolved
    assert asyncio.run(server.transcribe(name="youtube/clip.mp4")) == "Hello world transcript."
    assert asyncio.run(server.get_transcript(name="youtube/clip.mp4")) == "Hello world transcript."


def test_list_files_filters():
    _mock()
    assert len(asyncio.run(server.list_files())) == 2
    assert len(asyncio.run(server.list_files(service="youtube"))) == 1
    assert len(asyncio.run(server.list_files(label="fun"))) == 1


def test_configure_default_and_web_ui_precedence(monkeypatch):
    read = {"resolve", "list_files", "job_status", "get_transcript"}
    # Default: read + download + transcribe; destructive off.
    assert set(server.configure(None)) == read | {"download", "transcribe"}
    # Web-UI read-only → only read tools.
    assert set(server.configure({"read_only": True})) == read
    # Web-UI enables delete, disables download.
    got = set(server.configure({"tools": {"delete_file": True, "download": False}}))
    assert "delete_file" in got and "download" not in got
    # Env per-tool override beats the web UI.
    monkeypatch.setenv("VDL_MCP_TOOL_download", "on")
    monkeypatch.setenv("VDL_MCP_TOOL_delete_file", "off")
    got = set(server.configure({"tools": {"delete_file": True, "download": False}}))
    assert "download" in got and "delete_file" not in got
    monkeypatch.delenv("VDL_MCP_TOOL_download", raising=False)
    monkeypatch.delenv("VDL_MCP_TOOL_delete_file", raising=False)
    server.configure(None)  # restore for isolation


def test_effective_read_only_and_overrides(monkeypatch):
    monkeypatch.setattr(config, "READ_ONLY", True)
    assert config.effective("resolve", "read", "read") is True
    assert config.effective("download", "download", "write") is False
    monkeypatch.setattr(config, "READ_ONLY", False)
    # remote read-only also hides writes
    assert config.effective("download", "download", "write", {"read_only": True}) is False
    # per-tool env override wins over remote
    monkeypatch.setenv("VDL_MCP_TOOL_delete_file", "on")
    assert config.effective("delete_file", "delete", "delete", {"tools": {"delete_file": False}}) is True


def test_helpers_and_auth_errors():
    assert client.file_path("a b/c.mp4") == "/api/files/a%20b/c.mp4"
    config.DOMAIN_ALLOWLIST = ["youtube.com"]
    with pytest.raises(client.VdlError):
        client.check_domain("http://evil.com/x")
    client.check_domain("http://www.youtube.com/x")  # subdomain allowed
    config.DOMAIN_ALLOWLIST = []
    _mock()
    with pytest.raises(client.VdlError):
        asyncio.run(client.request("GET", "/api/secret"))  # 401 → friendly error
