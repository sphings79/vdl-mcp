# vdl-mcp — MCP server for vdl
# Copyright (C) 2026 sphings79
# SPDX-License-Identifier: AGPL-3.0-or-later
# Licensed under the GNU Affero General Public License v3.0 or later; see LICENSE.
"""Thin async HTTP client for the vdl REST API (authenticated by API token)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

import httpx

from . import config


class VdlError(RuntimeError):
    """A friendly, assistant-readable error."""


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {config.TOKEN}"} if config.TOKEN else {}


async def request(method: str, path: str, *, timeout: float | None = None, **kwargs: Any) -> httpx.Response:
    """Call the vdl API and turn auth/HTTP failures into readable errors."""
    async with httpx.AsyncClient(
        base_url=config.URL, headers=_headers(),
        timeout=timeout or config.TIMEOUT, follow_redirects=False,
    ) as http:
        try:
            r = await http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise VdlError(f"Could not reach vdl at {config.URL}: {exc}") from exc

    loc = r.headers.get("location", "")
    if r.status_code in (401, 403) or (r.status_code in (302, 307) and "/login" in loc):
        raise VdlError(
            "Not authorized. Set VDL_TOKEN to your vdl API token "
            "(in vdl: Settings → API token → create)."
        )
    if r.status_code >= 400:
        raise VdlError(f"vdl returned HTTP {r.status_code}: {r.text[:300]}")
    return r


def file_path(name: str) -> str:
    """Build /api/files/<name> with each path segment encoded but slashes kept."""
    return "/api/files/" + "/".join(quote(p) for p in name.split("/"))


def check_domain(url: str) -> None:
    """Enforce the optional domain allowlist (guards arbitrary-URL downloads)."""
    if not config.DOMAIN_ALLOWLIST:
        return
    host = (urlparse(url).hostname or "").lower()
    if not any(host == d or host.endswith("." + d) for d in config.DOMAIN_ALLOWLIST):
        raise VdlError(
            f"Domain '{host}' is not allowed. Add it to VDL_MCP_DOMAIN_ALLOWLIST "
            "or clear that variable to allow any host."
        )
