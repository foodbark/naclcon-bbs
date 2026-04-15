# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deploying Changes

There is no build step. Changes are deployed by rsyncing files to the live Synchronet installation:

```bash
rsync -av /home/ubuntu/naclcon-bbs/ctrl/ /sbbs/ctrl/
rsync -av /home/ubuntu/naclcon-bbs/mods/ /sbbs/mods/
rsync -av /home/ubuntu/naclcon-bbs/text/ /sbbs/text/
rsync -av /home/ubuntu/naclcon-bbs/data/ /sbbs/data/
```

Synchronet picks up most JS module changes on next execution without a full restart. Config (`.ini`) changes may require a reload from the sysop menu (`!` in the BBS).

To run a module directly (e.g., regenerate speaker bulletins):
```bash
/sbbs/exec/jsexec mods/exec/post_speakers.js
```

To test the BBS:
```bash
ssh bbs.naclcon.com -p 2222
# or by IP while DNS is pending:
ssh 100.51.222.185 -p 2222
```

## Synchronet Reference

**Always consult the Synchronet wiki when working with config, scripting, or BBS behavior.**

Wiki base URL: https://wiki.synchro.net

Key sections for this repo:
- https://wiki.synchro.net/scripting:index — JavaScript scripting API
- https://wiki.synchro.net/module:index — Standard JS modules (useful when overriding them)
- https://wiki.synchro.net/ref:atcodes — `@code` substitution reference (used in text/menu files)
- https://wiki.synchro.net/ref:ars — ARS (Access Requirement Strings)
- https://wiki.synchro.net/config:sbbs — Main configuration reference

Key wiki pages are also cached locally in `/sbbs/docs/wiki/` (named `namespace--page.md`). Check the local cache first via `/sbbs/docs/wiki/INDEX.md`; fetch live if the topic isn't there.

## Architecture

This is a **Synchronet v3.21 BBS** with custom JavaScript modules. Synchronet is the core engine; this repo contains only configuration and extensions.

### The mods/ Override Pattern

**Never edit files under `/sbbs/exec/` or `/sbbs/text/` directly.** Synchronet resolves modules by checking `mods/` before `exec/`, so any stock file can be overridden by placing a copy in `mods/`. All NaClCON customizations must live in this repo and be deployed via rsync — edits made directly to `/sbbs/` are untracked and will be lost or cause confusion.

To override a stock Synchronet module (e.g. `exec/logon.js`): copy it to `mods/logon.js` in this repo, make your changes there, and rsync to deploy.

### Directory Layout

- `ctrl/` — Synchronet config files (`.ini`). `pelican.ini` holds the Claude API key and is gitignored.
- `mods/` — Custom JS modules. Synchronet checks here before `/sbbs/exec/`, so files here override stock modules.
- `mods/exec/` — Modules invoked directly as commands (e.g., bulletin generators).
- `mods/load/` — Auto-loaded utility modules.
- `text/` — ANSI art, menus, and message text files displayed to users.
- `data/` — Runtime data (message bases, per-user history). `data/user/pelican_*.json` are created at runtime.

### The Pelican (Claude AI Integration)

The AI chatbot is the primary custom feature. It is split across two files:

- **`mods/pelican.js`** — 1-on-1 chat. Each user gets a persistent history file at `data/user/pelican_NNNN.json` (where `NNNN` is the user number). Keeps last 10 exchange pairs. 300-token response limit.
- **`mods/multichat_pelican.js`** — Full reimplementation of Synchronet's `bbs.multinode_chat()`. Pelican responds when addressed by name (`pelican`/`peli`) or when ≤3 users are in the channel. Shared history at `data/user/pelican_chan.json`, 30-message window, 150-token responses.

Both read `ctrl/pelican.ini` for the API key, model (Haiku), and token limits. The Pelican persona is a sassy southern coastal Peli-hen.

### Chat Section Override

`mods/chat_sec.js` replaces the stock Synchronet chat module. It intercepts the 'T' key (routes to `pelican.js`) and 'J' key (routes to `multichat_pelican.js`), so the AI integration hooks in without modifying Synchronet core.

### Shell System

Two shells are enabled (configured in `ctrl/main.ini` via `shell_list`):
- **Classic Shell** — Stock Synchronet terminal menu.
- **Lightbar Shell** (`mods/lbshell.js`) — Deuce's Lightbar Shell, heavily customized (2700+ lines) with NaClCON theming. This is the primary custom shell.

### Color Scheme

NaClCON brand palette using Synchronet Ctrl-A (`\x01`) color codes:

| Color | Ctrl-A Code | Use |
|-------|-------------|-----|
| Bright Magenta | `\x01h\x01m` | Primary accent, box borders |
| Hot Pink / Bright Red | `\x01h\x01r` | Highlights |
| Bright Yellow | `\x01h\x01y` | Info, hotkeys, BBS name |
| Bright White | `\x01h\x01w` | Body text |
| Dark Gray | `\x01h\x01k` | Subtle text, borders |

Standard ANSI escapes also apply: bright magenta = `\x1b[1;35m`, hot pink = `\x1b[1;31m`, bright yellow = `\x1b[1;33m`.

### Security Notes

- `text/ip-silent.can` — IPs silently dropped before Synchronet handles them. Add malicious IPs here.
- `text/host.can` / `text/ip.can` — Standard Synchronet access control lists.
- Login throttling is configured in `ctrl/main.ini`: hack threshold 5, temp ban after 20 attempts (15 min), permanent filter after 50.
- OS SSH (port 22) is restricted to sysop IP via AWS Security Group. BBS SSH is on port 2222.
