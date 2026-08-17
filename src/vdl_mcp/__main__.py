# vdl-mcp — MCP server for vdl
# Copyright (C) 2026 sphings79
# SPDX-License-Identifier: AGPL-3.0-or-later
# Licensed under the GNU Affero General Public License v3.0 or later; see LICENSE.
"""Allow `python -m vdl_mcp`."""

from .server import main

if __name__ == "__main__":
    main()
