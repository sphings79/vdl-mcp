# vdl-mcp — MCP server for vdl
# Copyright (C) 2026 sphings79
# SPDX-License-Identifier: AGPL-3.0-or-later
# Licensed under the GNU Affero General Public License v3.0 or later; see LICENSE.
"""MCP server exposing vdl to AI assistants.

Which tools are exposed is decided at startup by ``configure()``, combining:
env overrides, the web-UI config from vdl (Settings → MCP), and group defaults.
Read + Download + Transcribe are on by default; Delete + Bulk + Settings off.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastmcp import FastMCP

from . import config
from .client import VdlError, check_domain, file_path, request

mcp = FastMCP("vdl")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


async def _find_rel_name(basename: str) -> str | None:
    """Look up a file's downloads-relative path (folder/name) by its basename."""
    r = await request("GET", "/api/files")
    matches = [f for f in r.json().get("files", []) if f.get("basename") == basename]
    if not matches:
        return None
    matches.sort(key=lambda f: f.get("modified", 0), reverse=True)
    return matches[0].get("name")


# --------------------------------------------------------------------------
# Tool implementations (plain functions; registered in configure())
# --------------------------------------------------------------------------


async def resolve(url: str) -> dict:
    """[read] Analyze a link and list the available media items and qualities — WITHOUT downloading.

    Use this to preview what a URL contains before calling download.
    """
    check_domain(url)
    r = await request("POST", "/api/resolve", json={"url": url})
    d = r.json()
    items = []
    for it in d.get("items", []):
        qualities = sorted({v.get("label") for v in it.get("variants", []) if v.get("label")})
        items.append({
            "item_id": it.get("id"), "title": it.get("title"), "kind": it.get("kind"),
            "duration_seconds": it.get("duration"), "qualities": qualities,
        })
    return {"title": d.get("title"), "author": d.get("author"),
            "source_url": d.get("source_url"), "items": items}


async def list_files(query: str = "", service: str = "", label: str = "", limit: int = 50) -> list[dict]:
    """[read] List downloaded files in vdl. Optional filters: query (name/label substring),
    service (e.g. youtube), label. Returns name, size, duration, labels, in_feed."""
    r = await request("GET", "/api/files")
    q = query.lower()
    out = []
    for f in r.json().get("files", []):
        name = f.get("name", "")
        labels = [lb.get("text") for lb in f.get("labels", [])]
        if service and name.split("/")[0] != service:
            continue
        if label and label not in labels:
            continue
        if q and q not in name.lower() and not any(q in (lb or "").lower() for lb in labels):
            continue
        out.append({"name": name, "size_bytes": f.get("size"), "duration_seconds": f.get("duration"),
                    "labels": labels, "in_feed": f.get("in_feed", False)})
    out.sort(key=lambda f: f["name"])
    return out[: max(1, min(limit, 500))]


async def job_status(job_id: str = "") -> Any:
    """[read] Status of a download job by id, or the list of all current jobs if no id is given."""
    if job_id:
        return (await request("GET", f"/api/jobs/{job_id}")).json()
    r = await request("GET", "/api/jobs")
    return r.json().get("jobs", r.json())


async def get_transcript(name: str) -> str:
    """[read] Return the transcript text (.txt) of a downloaded file, if it has been transcribed.
    If none exists yet, tells you to run transcribe(name) first."""
    stem = name.rsplit(".", 1)[0]
    try:
        return (await request("GET", file_path(stem + ".txt"))).text
    except VdlError:
        return "No transcript found for this file yet. Use transcribe(name) to create one."


async def download(url: str, audio: bool = False, section: str = "",
                   wait: bool = True, timeout_seconds: int = 900) -> dict:
    """[writes] Download a video or audio from a URL into vdl (best quality).

    - audio=True downloads MP3 (audio only).
    - section like '0:30-1:00' clips a part.
    - wait=True (default) waits for completion and returns the resulting file 'name'
      (use it with transcribe/get_transcript). wait=False returns immediately with a job_id.
    """
    check_domain(url)
    r = await request("POST", "/api/download", json={"url": url, "audio": audio, "section": section})
    jobs = r.json().get("jobs", [])
    if not jobs:
        raise VdlError("No download job was started (nothing resolvable at that URL?).")
    jid = jobs[0].get("id")
    if not wait:
        return {"job_id": jid, "state": jobs[0].get("state"), "waited": False}
    deadline = time.monotonic() + max(10, timeout_seconds)
    while time.monotonic() < deadline:
        j = (await request("GET", f"/api/jobs/{jid}")).json()
        state = j.get("state")
        if state in ("done", "failed", "cancelled"):
            rel = await _find_rel_name(j.get("filename", "")) if state == "done" else None
            return {"job_id": jid, "state": state, "name": rel,
                    "filename": j.get("filename"), "error": j.get("error") or None}
        await asyncio.sleep(2)
    return {"job_id": jid, "state": "timeout", "note": "still running — check later with job_status(job_id)"}


async def transcribe(name: str, language: str = "") -> str:
    """[writes] Transcribe a downloaded file locally with Whisper and return the text.

    'name' is the downloads-relative path from list_files/download (e.g. 'youtube/clip.mp4').
    Requires a Whisper model set in vdl (Settings → Transcription). Can take a while.
    """
    r = await request("POST", file_path(name) + "/transcribe", timeout=1800)
    txt_name = r.json().get("txt")
    if not txt_name:
        raise VdlError("Transcription did not produce a text file.")
    return (await request("GET", file_path(txt_name))).text


async def delete_file(name: str) -> dict:
    """[deletes] Delete a downloaded file (off by default; enable in vdl's MCP tab or VDL_MCP_ALLOW_DELETE)."""
    return (await request("DELETE", file_path(name))).json()


async def bulk(action: str, names: list[str], text: str = "", color: str = "#5b8cff") -> dict:
    """[writes/deletes] Bulk action on many files (off by default).

    action: 'delete' | 'feed_add' | 'feed_remove' | 'label_add' | 'label_remove'.
    """
    payload: dict[str, Any] = {"action": action, "names": names, "color": color}
    if text:
        payload["text"] = text
    return (await request("POST", "/api/files/bulk", json=payload)).json()


async def get_settings() -> dict:
    """[read] Read vdl settings, secrets masked (off by default)."""
    r = await request("GET", "/api/settings")
    return r.json().get("settings", r.json())


# name, function, group, kind — kept in sync with vdl's MCP tab catalog.
TOOLS: list[tuple[str, Any, str, str]] = [
    ("resolve", resolve, "read", "read"),
    ("list_files", list_files, "read", "read"),
    ("job_status", job_status, "read", "read"),
    ("get_transcript", get_transcript, "read", "read"),
    ("download", download, "download", "write"),
    ("transcribe", transcribe, "transcribe", "write"),
    ("delete_file", delete_file, "delete", "delete"),
    ("bulk", bulk, "bulk", "write"),
    ("get_settings", get_settings, "settings", "read"),
]

_REGISTERED: set[str] = set()


def configure(remote: dict | None = None) -> list[str]:
    """(Re)register tools according to env + the web-UI config. Idempotent."""
    for name, fn, group, kind in TOOLS:
        want = config.effective(name, group, kind, remote)
        if want and name not in _REGISTERED:
            mcp.add_tool(fn)
            _REGISTERED.add(name)
        elif not want and name in _REGISTERED:
            mcp.local_provider.remove_tool(name)
            _REGISTERED.discard(name)
    return sorted(_REGISTERED)


def main() -> None:
    """Console entry point — fetch the web-UI config, register tools, run over stdio."""
    configure(config.fetch_remote())
    mcp.run()


if __name__ == "__main__":
    main()
