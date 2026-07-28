# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deploying Changes

There is no build step. Changes are deployed by rsyncing files to the live Synchronet installation:

```bash
rsync -av /home/ubuntu/naclcon-bbs/ctrl/ /sbbs/ctrl/
rsync -av /home/ubuntu/naclcon-bbs/mods/ /sbbs/mods/
rsync -av /home/ubuntu/naclcon-bbs/text/ /sbbs/text/
rsync -av /home/ubuntu/naclcon-bbs/data/ /sbbs/data/
rsync -av /home/ubuntu/naclcon-bbs/scripts/ /sbbs/scripts/
rsync -av /home/ubuntu/naclcon-bbs/webv4/   /sbbs/webv4/
rsync -av /home/ubuntu/naclcon-bbs/xtrn/    /sbbs/xtrn/
```

Synchronet picks up most JS module changes on next execution without a full restart. Config (`.ini`) changes may require a reload from the sysop menu (`!` in the BBS).

To run a module directly (e.g., regenerate speaker bulletins):
```bash
/sbbs/exec/jsexec mods/exec/post_speakers.js
```

To test the BBS:
```bash
ssh naclconbbs.net -p 2222
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

NaClCON 2026 ran May 31 - June 2, 2026 and is over. The board now runs year-round as the sysop's personal BBS with the con preserved as a read-only archive, so **write copy in the past tense** and point people at the archive. The board calls itself **unofficial**, never "semi-official"; that wording is a deliberate choice to avoid implying endorsement by organisers who have since fallen out, so don't "correct" it.

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
- `webv4/` — NaClCON branding overrides for the Synchronet web frontend. Mirrors the layout under `/sbbs/webv4/`. Use the override hooks rather than forking stock files: `webv4/root/css/custom.css` is auto-linked by `index.xjs` after `style.css`, and `webv4/mods/components/header.xjs` is auto-loaded by `loadComponent()` ahead of stock `webv4/components/`. The web frontend depends on user #2 (`Guest`) being **active** — if the home page renders empty, `journalctl -u sbbs` will show `!DELETED OR INACTIVE USER #2: Guest`; clear `USER_INACTIVE` via jsexec.

  > **Pages must NOT wrap their content in `<div class="container">`.** `index.xjs` calls `writePage()` from inside a `col-xs-12 col-sm-9`, and a Bootstrap 3 `.container` is *fixed* width (750/970/1170px). Nested in that column it ends up wider than its parent on desktop and spills right, so the sidebar appears to cut into the page content. Every stock page emits straight into the column. Only components rendered outside the grid, like `mods/components/header.xjs` and the navbar, get a `.container`.

### The Pelican (Claude AI Integration)

The AI chatbot is the primary custom feature. It is split across four files:

The Pelican relocated from Carolina Beach to **Missoula, MT** in July 2026 (the sysop moved; the board followed). Her knowledge is split by location: `ctrl/pelican_local.txt` is where she is *from* (framed as memory by its own preamble), `ctrl/pelican_missoula.txt` is where she *is*. Knowledge loads in the order `naclcom → local → missoula → foodbark → news` into `STATIC_KNOWLEDGE`; if you add a knowledge file, add it to **`mods/load/pelican_brain.js` and to `mods/multichat_pelican.js`** (multichat still carries its own copy).

NaClCON 2026 is over. Both the brain and multichat compute a count **up** from the closing day and instruct her to use the past tense. There is no date string to maintain, and nothing should reintroduce a countdown.

- **`mods/load/pelican_brain.js`** — the shared brain: persona prompt, knowledge loading, cache breakpoints, history read/write, input guards, and the Claude API call. Used by the terminal module and the web endpoint so the persona has one source of truth. Exposes `PelicanBrain.{config, ask, load_history, save_history, is_injection, system_blocks, MAX_INPUT}`.

  > **Block order is load-bearing for prompt caching.** `system_blocks(venue)` emits `[CORE_PERSONA (cached), STATIC_KNOWLEDGE (cached), venue coda + volatile]`. The two cached blocks must stay a **byte-identical prefix across venues**, which is exactly why anything venue-specific or time-varying is appended *last*. Putting the venue text earlier would fork the cache between terminal and web and silently double the cache-write cost.

- **`mods/pelican.js`** — terminal 1-on-1 chat. Each user gets a persistent history file at `data/user/pelican_NNNN.json` (where `NNNN` is the user number). Keeps last 10 exchange pairs, 20 API calls per session. This file is now only the terminal UI (input wrapping, word wrap, Ctrl-A colors).
- **`mods/multichat_pelican.js`** — Full reimplementation of Synchronet's `bbs.multinode_chat()`. Pelican responds when addressed by name (`pelican`/`peli`) or when ≤3 users are in the channel. Shared Pelican history at `data/user/pelican_chan.json`, 30-message window, 150-token responses. Public chat is also persisted to `/sbbs/data/multichat_scrollback.txt` (last 90 rendered lines) and replayed under a `── scrollback ──` header on join. Slash commands: `/W <alias> <text>` (whisper to one online user, alias-matched via `system.matchuser`, not persisted), `/L` (list who's in the room), `/Q` (quit), `/?` (re-show menu via `bbs.menu("multchat")`). `^U` and `^P` pass through to Synchronet's built-in user-list and private-message dialogs. Menu file: `text/menu/multchat.msg` (NaClCON-branded).

- **`webv4/root/api/pelican.ssjs` + `webv4/mods/pages/004-pelican.xjs`** — web chat, reachable at `/?page=004-pelican.xjs` (webv4 routes by full filename, not by the short page name). The endpoint is **logged-in only**: guests get a 401 from the API and a "log in" panel on the page, because it spends API money on every call and the board is publicly reachable. Per-user daily cap via `web_daily_limit` in `pelican.ini`, counted in `data/user/pelican_webquota_NNNN.json`.

  It deliberately reads and writes the **same** `data/user/pelican_NNNN.json` the terminal uses, so a conversation started in SyncTERM continues in the browser. The `HELLO` opener both front ends send is filtered out of the transcript the page renders, since the user never saw it on screen. Styles live in `custom.css` under "Pelican web chat".

All of these read `ctrl/pelican.ini` for the API key, model (Haiku), and token limits. The Pelican persona is a sassy southern coastal Peli-hen.

### ANSI Art to PNG (`scripts/ans2png.py`)

The art in `art/` is **truecolor half-block ANSI**: every character cell holds two stacked pixels (`▀`/`▄` with `38;2;r;g;b` foreground and `48;2;r;g;b` background), so an 80x56 cell grid is really an 80x112 RGB bitmap. `scripts/ans2png.py` decodes that back into a pixel-exact PNG, which is how the web chat gets her portrait without needing a CP437 webfont.

Two dialects exist in `art/` and the script handles both:
- **UTF-8** (`closeup.ans`, `XXXXX.ans`, `1XXXX.ans`) — real `U+2580`/`U+2584` characters, LF line breaks.
- **CP437** (`closeup02.ans`, `logo.ans`) — raw byte `0xDF`, **no line breaks at all** (it relies on the terminal wrapping at 80 columns, so the decoder must wrap manually), plus a trailing SAUCE record starting at `0x1A` that must be stripped.

Generated PNGs are tiny (80px wide) and **must** be scaled with `image-rendering: pixelated`, or the blocks turn to mush.

`scripts/img2ans.py` is the exact inverse: it encodes any image or animation into the same half-block ANSI. `--verify` round-trips the result back through `ans2png.py` and asserts the pixels match, which is the quickest way to confirm a change to either script did not break the pair.

> **Both scripts are vendored from the standalone `halfblock` repo and should be fixed upstream first**, then copied back. That repo has a round-trip test suite (`python3 tests/test_roundtrip.py`) covering both glyph encodings, all three row conventions and several widths; the copies here have no tests of their own. The suite caught two real decoder bugs plus a regression that silently mangled `art/logo.ans`, none of which the board art alone would have surfaced.

- **At exactly 80 columns it emits no line breaks**, relying on terminal auto-wrap. This is why `art/logo.ans` and `art/closeup02.ans` have zero newlines; adding one costs a blank line per row on an 80-column terminal. Narrower output gets CRLF.

  > **That default only holds inside SyncTERM.** Auto-wrap art shears diagonally in any window that is not exactly 80 columns, which is every modern terminal. Use `--positioned` for anything that will be viewed outside a BBS session: it prefixes each row with an absolute `ESC[row;1H` and a clear-to-EOL, so width stops mattering. It is also the right choice for animation, since frames then land exactly on top of each other instead of drifting.

- `--space` encodes with background-coloured ASCII spaces instead of half blocks, one cell per pixel. Nothing outside `0x20-0x7E`, so it cannot break on a font missing `U+2580` or on a terminal that is not in UTF-8 mode. Costs half the vertical resolution; `fit()` halves the pixel height to compensate, so the aspect ratio matches half-block output exactly. Note it is **entirely** background colour, so a terminal without truecolor renders it as blank space rather than as wrong colours.
- It only emits the parts of an SGR sequence that actually changed. Re-stating both colours plus a reset per cell, as the older art does, is what makes those files 100KB+.
- Defaults to CP437 (raw `0xDF`) for SyncTERM, written as latin-1 so bytes round-trip; `--utf8` emits `U+2580` instead.

**`text/nyan/` + `mods/nyan.js`** — a 12-frame animation at 80x16 cells, played as `*nyan` or `jsexec mods/nyan.js <loops>`. Each frame is a full redraw because roughly 90% of cells change between frames, so there is nothing worth delta-encoding. That costs about 28KB per frame, 700KB per two-loop run. The player sets `console.output_rate = 0` (as `pelican.js` does) so the baud emulation does not throttle it, and falls back to plain `write()` when `console` is undefined so it can be tested headlessly under jsexec. `text/nyan/ascii/` holds the `--space` variant; pass `ascii` to use it.

> **The charset default is decided by whether a session exists.** `console` is defined in a BBS session and undefined under jsexec, and the player keys off that. In a session the CP437 bytes go out untouched, because Synchronet does its own translation for UTF-8 terminals. Under jsexec nothing translates, so the player emits UTF-8 by default; a raw `0xDF` reaching a modern terminal renders as a replacement character. `cp437` and `utf8` override.
>
> Both of the bugs this animation shipped with came from assuming SyncTERM's environment applied outside it: no-newline art needs an exactly-80-column terminal, and raw CP437 needs Synchronet in the path. **Anything under `text/` that might get viewed with `cat` or `jsexec` rather than through the BBS carries both assumptions.**

### Message Groups and Sub-Board Codes

**A sub's internal code is the group's `code_prefix` + the ini section suffix, and the message base filename derives from that code.** `[grp:Local]` has `code_prefix=LOCAL-`, so `[sub:Local:CTF]` is code `LOCAL-CTF` stored in `data/subs/local-ctf.*`.

This makes moving a sub between groups dangerous: if the destination group has a different prefix, the code changes, the filename changes, and every message in that base is orphaned. When the five NaClCON sub-boards moved into `[grp:NaClCON2026]` (the read-only con archive, `post_ars=SYSOP`), that group was **deliberately given the same `code_prefix=LOCAL-`** so the codes and data files were untouched. Duplicate prefixes across groups are fine provided the full codes stay unique.

After editing `ctrl/msgs.ini`, `sbbs` needs a restart to pick it up. Expect `!ERROR 98 ... port 23: Address already in use` on the way back up: it retries every 15s up to 5 times and usually binds on attempt 3. Don't restart again; check `sudo ss -tlnp | grep sbbs` (sudo is needed to see the process) and confirm both `0.0.0.0:23` and `[::]:23`.

### The Conditions Strip (two renderers, keep in sync)

The one-line weather/conditions strip is built from `data/weather_tides.txt` (key=value, refreshed every 30 min by cron) and rendered in **two** places that must agree:

- `render_weather_strip_color()` / `_plain()` in `scripts/pelican_weather_tides.py`: writes it into the logon splash files.
- `nc_weather_strip()` in `mods/lbshell.js`: draws it live on the Lightbar status row.

Change one, change the other. They emit **byte-identical** output and should stay that way; verify by hex-diffing both against the same `data/weather_tides.txt` snapshot, not by eye.

They briefly diverged: the AQI colours for "Sensitive Groups" and "Hazardous" need `\x01n` to clear the high-intensity bit, `\x01n` also clears the **background**, and the lbshell banner rows used to be painted magenta (`console.attributes=0x5F`), so that renderer had to re-assert `\x015`. The banner background was removed, so both are plain again.

**Width budget:** six fields fit 79 columns with ~3 to spare. A seventh will wrap an 80-column terminal.

`scripts/pelican_weather_tides.py` keeps its name for crontab stability despite Montana having no tides. Sources: NWS (temp/precip/wind), Open-Meteo (US AQI + PM2.5), USGS gauge `12340500` "Clark Fork above Missoula", *not* `12353000` ("below Missoula"), which is past the Bitterroot confluence and reads much higher.

### BullsEye Bulletin Config

`mods/bullseye.js` overrides the stock module and extends `text/bullseye.cfg`: a line starting with `#` is a non-selectable section header, and `path|Label` sets an explicit menu label instead of deriving one from the filename. Numbering skips headers and stays continuous. Line 1 is still the print-mode expression (`P_SEEK`).

> **`mods/exec/` is NOT an override path.** `xtrn.ini` invokes this module as `cmd=*bullseye`, and Synchronet resolves a `*name` module by searching `mods/name.js` then `exec/name.js`. It never looks in `mods/exec/`. A file at `mods/exec/bullseye.js` is therefore dead: stock `exec/bullseye.js` runs instead. `mods/exec/` is only for modules invoked by explicit path, like `jsexec mods/exec/post_speakers.js`.
>
> This bit once already: `mods/exec/bullseye.js` was edited for months while the board actually ran a hand-edited `/sbbs/exec/bullseye.js`, so changes appeared to do nothing until the cfg format changed and the mismatch surfaced as "file not found". **When a module change seems to have no effect, check which path Synchronet is really resolving before debugging the code.**

### Chat Section Override

`mods/chat_sec.js` replaces the stock Synchronet chat module. It intercepts the 'T' key (routes to `pelican.js`) and 'J' key (routes to `multichat_pelican.js`), so the AI integration hooks in without modifying Synchronet core.

### New-User Registration Override

`mods/newuser_prompts.js` replaces stock `exec/newuser_prompts.js` for two behaviors stock can't express via `[newuser] questions=` bits:

- Real name accepts blank (no validation loop on empty input).
- Email accepts blank; `get_netmail_forwarding` only runs if a non-empty address was entered.

The bit field in `ctrl/main.ini` is `questions=0xa4d23` — drops `UQ_HANDLE` (no separate handle prompt; handle auto-fills from alias), drops `UQ_SEX` and `UQ_BIRTH`, sets `UQ_NOUPRLWR` (preserve case in alias/real-name input). Prompt wording for alias / real name / location / email is customized in `ctrl/text.dat` (string IDs 338, 339, 346, 500). text.dat is tracked in the repo specifically because of those four customized strings — most of the file is stock.

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
