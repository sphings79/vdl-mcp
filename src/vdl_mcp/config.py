# vdl-mcp — MCP server for vdl
# Copyright (C) 2026 sphings79
# SPDX-License-Identifier: AGPL-3.0-or-later
# Licensed under the GNU Affero General Public License v3.0 or later; see LICENSE.
"""Configuration via environment variables.

Everything is toggleable with sensible defaults: safe tool groups (read,
download, transcribe) are ON, risky ones (delete, bulk, settings) are OFF.
"""

from __future__ import annotations

import os

import httpx


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, "true" if default else "false").strip().lower() in ("1", "true", "yes", "on")


# --- Connection to your vdl instance ---------------------------------------
URL = os.getenv("VDL_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.getenv("VDL_TOKEN", "").strip()          # vdl Settings → API token → create
TIMEOUT = float(os.getenv("VDL_MCP_TIMEOUT", "30"))  # default per-request timeout (s)

# --- Read-only mode --------------------------------------------------------
# Like a kill switch: exposes only "read" tools (no download/transcribe/delete/
# bulk). Overrides everything below.
READ_ONLY = _bool("VDL_MCP_READ_ONLY", False)

# --- Tool groups (schaltbar / toggleable) ----------------------------------
ALLOW: dict[str, bool] = {
    "read":       _bool("VDL_MCP_ALLOW_READ", True),        # resolve, list_files, job_status, get_transcript
    "download":   _bool("VDL_MCP_ALLOW_DOWNLOAD", True),    # download
    "transcribe": _bool("VDL_MCP_ALLOW_TRANSCRIBE", True),  # transcribe (Whisper)
    "delete":     _bool("VDL_MCP_ALLOW_DELETE", False),     # delete_file
    "bulk":       _bool("VDL_MCP_ALLOW_BULK", False),       # bulk actions
    "settings":   _bool("VDL_MCP_ALLOW_SETTINGS", False),   # read settings
}


def fetch_remote() -> dict | None:
    """Best-effort fetch of the tool config from vdl (Settings → MCP tab).

    Returns e.g. ``{"read_only": false, "tools": {"download": true, ...}}`` or
    None if vdl is unreachable / the endpoint is absent (older vdl).
    """
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        r = httpx.get(f"{URL}/api/mcp/config", headers=headers, timeout=8, follow_redirects=False)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, dict) else None
    except Exception:
        pass
    return None


def effective(name: str, group: str, kind: str, remote: dict | None = None) -> bool:
    """Whether a tool is exposed. Precedence (highest first):

    1. **Read-only** — env ``VDL_MCP_READ_ONLY`` OR the web UI's read-only switch
       hides everything that is not a pure ``read`` tool.
    2. **Per-tool env override** — ``VDL_MCP_TOOL_<name>=on|off`` always wins.
    3. **Web UI** — the per-tool setting from vdl's MCP tab, if present.
    4. **Group flag** — the ``VDL_MCP_ALLOW_<group>`` fallback.
    """
    read_only = READ_ONLY or bool(remote and remote.get("read_only"))
    if read_only and kind != "read":
        return False
    override = os.getenv(f"VDL_MCP_TOOL_{name}")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes", "on")
    if remote and isinstance(remote.get("tools"), dict) and name in remote["tools"]:
        return bool(remote["tools"][name])
    return ALLOW.get(group, False)


# --- Optional guard against arbitrary-URL downloads (prompt-injection) ------
# Comma-separated host suffixes; empty = allow any host.
DOMAIN_ALLOWLIST = [d.strip().lower() for d in os.getenv("VDL_MCP_DOMAIN_ALLOWLIST", "").split(",") if d.strip()]
