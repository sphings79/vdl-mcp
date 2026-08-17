<h1 align="center">vdl-mcp</h1>

<p align="center">
  <strong>MCP-Server für <a href="https://github.com/sphings79/vdl">vdl</a> — lass KI-Assistenten (Claude &amp; Co.) Videos über deine selbst gehostete vdl-Instanz auflösen, herunterladen und <em>transkribieren</em>.</strong>
</p>

<p align="center">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-server-5b8cff">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Lizenz: AGPL v3" src="https://img.shields.io/badge/license-AGPL--3.0-blue">
</p>

<p align="center"><a href="README.md">English</a> · <strong>Deutsch</strong></p>

`vdl-mcp` verbindet einen KI-Assistenten mit deinem eigenen [vdl](https://github.com/sphings79/vdl)-Server über das [Model Context Protocol](https://modelcontextprotocol.io). Der eigentliche Clou ist die **Whisper-Synergie**:

> **Download → Transkript → der Assistent *versteht* den Inhalt.**

So sind Sätze wie diese möglich:

- *„Lade dieses YouTube-Video und fass es zusammen."*
- *„Zieh das Kochvideo und schreib mir das Rezept als Liste."*
- *„Was wurde in diesem Interview über X gesagt?"*
- *„Lade den Ton dieses Vortrags und gib mir die Kernpunkte."*

## Wie es funktioniert

Ein kleiner **stdio-MCP-Server**, der über die REST-API mit vdl spricht und sich mit deinem vorhandenen **API-Token** anmeldet. In vdl selbst läuft nichts Zusätzliches.

Die Tool-Gruppen sind **schaltbar mit sicherer Vorbelegung**:

| Gruppe | Tools | Standard |
|---|---|---|
| **Lesen** | `resolve`, `list_files`, `job_status`, `get_transcript` | ✅ an |
| **Download** | `download` | ✅ an |
| **Transkribieren** | `transcribe` | ✅ an |
| **Löschen** | `delete_file` | ❌ aus |
| **Massenaktion** | `bulk` | ❌ aus |
| **Einstellungen** | `get_settings` | ❌ aus |

Eine deaktivierte Gruppe ist für den Assistenten **unsichtbar**.

## Voraussetzungen

- Eine laufende **[vdl](https://github.com/sphings79/vdl)**-Instanz.
- Ein **API-Token**: in vdl unter **Einstellungen → API-Token → erzeugen**, kopieren.

## Installation

Mit [pipx](https://pipx.pypa.io) (legt `vdl-mcp` in den PATH):

```bash
pipx install git+https://github.com/sphings79/vdl-mcp
```

oder mit [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/sphings79/vdl-mcp
```

## In Claude Desktop einbinden

In die Claude-Desktop-Konfiguration (`claude_desktop_config.json`) eintragen:

```json
{
  "mcpServers": {
    "vdl": {
      "command": "vdl-mcp",
      "env": {
        "VDL_URL": "http://localhost:8000",
        "VDL_TOKEN": "dein-api-token"
      }
    }
  }
}
```

Claude Desktop neu starten — die vdl-Tools erscheinen. (Jeder MCP-fähige Client funktioniert gleich; einfach das `vdl-mcp`-Kommando über stdio starten.)

### Mit Docker betreiben

Lieber ein Container? Ein fertiges Image liegt in der GHCR — als Kommando nutzen:

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
        "VDL_TOKEN": "dein-api-token"
      }
    }
  }
}
```

Wichtig: `-i` (stdin offen halten für stdio) und — wenn vdl auf demselben Host läuft — `host.docker.internal`, damit der Container vdl erreicht.

## Keine Weboberfläche — bewusst so

`vdl-mcp` ist ein **stdio-Prozess**, den dein MCP-Client lokal startet. Er **öffnet keinen Netzwerk-Port**, hat also **keine Login-Seite und kein fail2ban** — es gibt nichts Eingehendes zu schützen. Sicherheitsmodell: **API-Token** privat halten, **destruktive Tools aus** lassen (Standard), optional eine **Domain-Allowlist** setzen. Anmeldung und Brute-Force-Schutz liegen in **vdl selbst** (das hat beides). Falls du `vdl-mcp` doch mal als entfernten HTTP-Server für mehrere Clients willst, ist das ein anderer Transport — dann ein Issue aufmachen.

## Tools

- **`resolve(url)`** — Link analysieren, Items und Qualitäten anzeigen (kein Download).
- **`download(url, audio=False, section="", wait=True)`** — beste Qualität (oder MP3); `section` wie `0:30-1:00` schneidet; `wait` gibt den fertigen Datei-`name` zurück.
- **`transcribe(name, language="")`** — Whisper-Transkription → Text (braucht ein Whisper-Modell in vdl).
- **`get_transcript(name)`** — Text eines bestehenden Transkripts zurückgeben.
- **`list_files(query, service, label, limit)`** — Downloads durchsuchen.
- **`job_status(job_id)`** — Download-Job prüfen.
- *(Standard aus)* `delete_file`, `bulk`, `get_settings`.

## Konfiguration (Umgebungsvariablen)

| Variable | Standard | Bedeutung |
|---|---|---|
| `VDL_URL` | `http://localhost:8000` | Basis-URL deiner vdl-Instanz |
| `VDL_TOKEN` | *(leer)* | vdl-API-Token (erforderlich) |
| `VDL_MCP_READ_ONLY` | `false` | **Not-Aus**: nur Lese-Tools (kein download/transcribe/delete/bulk) |
| `VDL_MCP_ALLOW_READ` | `true` | resolve/list/status/get_transcript |
| `VDL_MCP_ALLOW_DOWNLOAD` | `true` | download |
| `VDL_MCP_ALLOW_TRANSCRIBE` | `true` | transcribe |
| `VDL_MCP_ALLOW_DELETE` | `false` | Dateien löschen |
| `VDL_MCP_ALLOW_BULK` | `false` | Massenaktionen |
| `VDL_MCP_ALLOW_SETTINGS` | `false` | Einstellungen lesen |
| `VDL_MCP_TOOL_<name>` | *(nicht gesetzt)* | Pro-Tool-Override, z. B. `VDL_MCP_TOOL_download=off` — schlägt die Gruppe |
| `VDL_MCP_DOMAIN_ALLOWLIST` | *(leer = alle)* | Komma-getrennte Host-Endungen, von denen der Assistent laden darf |
| `VDL_MCP_TIMEOUT` | `30` | Standard-Timeout (Sekunden) |

Jedes Tool ist in seiner Beschreibung getaggt — **[read]**, **[writes]** oder **[deletes]** — damit du (und der Assistent) das Risiko auf einen Blick siehst.

**Auch über die vdl-Weboberfläche steuerbar:** in vdl unter **Einstellungen → Reiter MCP** jedes Tool an-/abschalten (mit Nur-Lese-Schalter und Risiko-Chips). `vdl-mcp` holt sich diese Config beim Start — dann sind keine Env-Variablen nötig; nach Änderungen `vdl-mcp` neu starten. Reihenfolge, ob ein Tool sichtbar ist: **Nur-Lese (Env oder UI) → Pro-Tool-Env-Override → Weboberfläche → Gruppen-Schalter**.

## Sicherheitshinweise

- Der Assistent handelt über deinen Token **als du** — halte ihn privat.
- **Destruktive Tools sind standardmäßig aus.** Bewusst aktivieren.
- Eine **beliebige URL** auf Zuruf des Assistenten zu laden, hat eine Prompt-Injection-Fläche. Setze `VDL_MCP_DOMAIN_ALLOWLIST` (z. B. `youtube.com,instagram.com`), um das einzugrenzen.
- Nur für Inhalte, die dir gehören oder für die du die Rechte/Erlaubnis hast — es gilt derselbe [Haftungsausschluss](https://github.com/sphings79/vdl#haftungsausschluss) wie bei vdl.

## Lizenz

**GNU Affero General Public License v3.0** (AGPL-3.0) — siehe [LICENSE](LICENSE). © 2026 sphings79
