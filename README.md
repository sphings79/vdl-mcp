<h1 align="center">vdl-mcp</h1>

<p align="center">
  <strong>MCP server for <a href="https://github.com/sphings79/vdl">vdl</a> — let AI assistants (Claude &amp; co.) resolve, download and <em>transcribe</em> videos through your self-hosted vdl instance.</strong>
</p>

<p align="center">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-server-5b8cff">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="License: AGPL v3" src="https://img.shields.io/badge/license-AGPL--3.0-blue">
</p>

<p align="center"><strong>English</strong> · <a href="README.de.md">Deutsch</a></p>

`vdl-mcp` connects an AI assistant to your own [vdl](https://github.com/sphings79/vdl) server over the [Model Context Protocol](https://modelcontextprotocol.io). The real power is the **Whisper synergy**:

> **Download → transcript → the assistant *understands* the content.**

So you can say things like:

- *"Download this YouTube video and summarize it."*
- *"Grab that cooking clip and write out the recipe as a list."*
- *"What was said about X in this interview?"*
- *"Download the audio of this talk and give me the key points."*

## How it works

It's a small **stdio MCP server** that talks to vdl's REST API and authenticates with your existing **API token**. Nothing runs inside vdl itself.

Tool groups are **toggleable with safe defaults**:

| Group | Tools | Default |
|---|---|---|
| **Read** | `resolve`, `list_files`, `job_status`, `get_transcript` | ✅ on |
| **Download** | `download` | ✅ on |
| **Transcribe** | `transcribe` | ✅ on |
| **Delete** | `delete_file` | ❌ off |
| **Bulk** | `bulk` | ❌ off |
| **Settings** | `get_settings` | ❌ off |

A disabled group is **invisible** to the assistant.

## Requirements

- A running **[vdl](https://github.com/sphings79/vdl)** instance.
- An **API token**: in vdl go to **Settings → API token → create**, and copy it.

## Install

With [pipx](https://pipx.pypa.io) (puts `vdl-mcp` on your PATH):

```bash
pipx install git+https://github.com/sphings79/vdl-mcp
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/sphings79/vdl-mcp
```

## Connect it to Claude Desktop

Add this to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vdl": {
      "command": "vdl-mcp",
      "env": {
        "VDL_URL": "http://localhost:8000",
        "VDL_TOKEN": "your-api-token"
      }
    }
  }
}
```

Restart Claude Desktop — the vdl tools appear. (Any MCP-capable client works the same way; just run the `vdl-mcp` command over stdio.)

### Run with Docker

Prefer a container? A prebuilt image is published to GHCR — use it as the command:

```json
{
  "mcpServers": {
    "vdl": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-e", "VDL_URL", "-e", "VDL_TOKEN",
               "ghcr.io/sphings79/vdl-mcp:latest"],
      "env": {
        "VDL_URL": "http://host.docker.internal:8000",
        "VDL_TOKEN": "your-api-token"
      }
    }
  }
}
```

Note the `-i` (keep stdin open for stdio) and, when vdl runs on the same host, `host.docker.internal` so the container can reach it.

## No web UI — by design

`vdl-mcp` is a **stdio** process launched locally by your MCP client. It **does not open a network port**, so it has **no login page and no fail2ban** — there is nothing inbound to protect. Its security model is: keep your **API token** private, leave **destructive tools off** (the defaults), and optionally set a **domain allowlist**. Authentication and brute-force protection live in **vdl itself**. (If you ever want a remote, multi-client HTTP server instead, that's a different transport — open an issue.)

## Tools

- **`resolve(url)`** — analyze a link, list items and available qualities (no download).
- **`download(url, audio=False, section="", wait=True)`** — download best quality (or MP3); `section` like `0:30-1:00` clips; `wait` returns the finished file `name`.
- **`transcribe(name, language="")`** — Whisper transcription → returns the text (requires a Whisper model set in vdl).
- **`get_transcript(name)`** — return an existing transcript's text.
- **`list_files(query, service, label, limit)`** — browse your downloads.
- **`job_status(job_id)`** — check a download job.
- *(off by default)* `delete_file`, `bulk`, `get_settings`.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `VDL_URL` | `http://localhost:8000` | Base URL of your vdl instance |
| `VDL_TOKEN` | *(empty)* | vdl API token (required) |
| `VDL_MCP_READ_ONLY` | `false` | **Kill switch**: expose only read tools (no download/transcribe/delete/bulk) |
| `VDL_MCP_ALLOW_READ` | `true` | resolve/list/status/get_transcript |
| `VDL_MCP_ALLOW_DOWNLOAD` | `true` | download |
| `VDL_MCP_ALLOW_TRANSCRIBE` | `true` | transcribe |
| `VDL_MCP_ALLOW_DELETE` | `false` | delete files |
| `VDL_MCP_ALLOW_BULK` | `false` | bulk actions |
| `VDL_MCP_ALLOW_SETTINGS` | `false` | read settings |
| `VDL_MCP_TOOL_<name>` | *(unset)* | Per-tool override, e.g. `VDL_MCP_TOOL_download=off` — beats the group flag |
| `VDL_MCP_DOMAIN_ALLOWLIST` | *(empty = any)* | comma-separated host suffixes the assistant may download from |
| `VDL_MCP_TIMEOUT` | `30` | default request timeout (seconds) |

Every tool is tagged in its description — **[read]**, **[writes]** or **[deletes]** — so both you and the assistant can see its risk at a glance.

**Manage it from vdl's web UI too:** in vdl go to **Settings → MCP tab** to toggle each tool (with a read-only master switch and risk chips). `vdl-mcp` fetches that config at startup, so no env vars are needed — restart `vdl-mcp` after changes. Precedence for whether a tool is exposed: **read-only (env or UI) → per-tool env override → web UI → group flag**.

## Security notes

- The assistant acts as **you** via your token — keep it private.
- **Destructive tools are off by default.** Enable them consciously.
- Downloading an **arbitrary URL** on an assistant's request has a prompt-injection surface. Set `VDL_MCP_DOMAIN_ALLOWLIST` (e.g. `youtube.com,instagram.com`) to restrict it.
- Only for content you own or have the rights/permission to download — the same [disclaimer](https://github.com/sphings79/vdl#disclaimer) as vdl applies.

## License

**GNU Affero General Public License v3.0** (AGPL-3.0) — see [LICENSE](LICENSE). © 2026 sphings79
