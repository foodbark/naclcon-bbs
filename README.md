# NaClCON BBS

Bulletin board sytem for [NaClCON 2026](https://naclcon.com) hacker conference in Carolina Beach, NC. May 31 - June 2, 2026.

> Play Hard. Hack Harder.

## Connect

```
ssh bbs.naclcon.com -p 2222
```

> DNS pending. Current IP: **34.229.165.250**

## Server

A Synchronet BBS (v3.21) running on AWS EC2 (Ubuntu 24.04). Spun up as a community hub for NaClCON attendees: message boards, file areas, chat, doors, and The Pelican.

- **Nodes**: 20 (supports 20 concurrent users) — upgrade instance to t3.medium before the con
- **Sysop**: foodbark

## AWS Security Group — Required Open Ports

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 22 | TCP | OS SSH | Restrict to sysop IP only |
| 2222 | TCP | BBS SSH (public) | Open to all |
| 80 | TCP | HTTP | Open to all |
| 443 | TCP | HTTPS | Open to all |
| 21 | TCP | FTP | Open to all |
| 70 | TCP | Gopher | Open to all |
| 119 | TCP | NNTP | Open to all |
| 1123 | TCP | WebSocket | Open to all |
| 11235 | TCP | WebSocket TLS | Open to all |

> Note: Gopher (70) and NNTP (119) are configured but currently disabled in
> `ctrl/services.ini` (`Enabled=false`). Open the ports when you enable them.

## Status

- [x] SSH access on port 2222
- [x] New user registration
- [x] NaClCON branding throughout
- [x] Local message boards
- [x] Chat, file areas, external doors
- [x] Security hardening (see below)
- [x] Shell restricted to Synchronet Classic + Deuce's Lightbar Shell
- [x] NaClCON color palette applied to both shells
- [x] The Pelican — Claude-powered AI chat bot (1-on-1 and multinode)
- [x] Speaker list bulletin and per-speaker message threads
- [x] Terminal-adaptive splash art at logon (wide ANSI art for large terminals >80 col, narrow art for 80-col terminals like SyncTERM; see `mods/logon.js`)
- [ ] CTF-related content
- [ ] Custom doors / programs

## Color Scheme

NaClCON brand palette mapped to CGA 16-color terminal codes:

| Color | CGA Index | Escape Code | Use |
|-------|-----------|-------------|-----|
| Bright Magenta | 13 | `\x1b[1;35m` | Primary accent |
| Dark Magenta | 5 | `\x1b[35m` | Secondary accent |
| Bright Red (hot pink) | 9 | `\x1b[1;31m` | Highlight |
| Dark Red | 1 | `\x1b[31m` | Dim highlight |
| Bright Yellow | 11 | `\x1b[1;33m` | Info / emphasis |
| Dark Yellow | 3 | `\x1b[33m` | Dim info |
| Bright White | 15 | `\x1b[1;37m` | Body text |
| Light Gray | 7 | `\x1b[37m` | Dim text |
| Dark Gray | 8 | `\x1b[1;30m` | Subtle / borders |
| Black | 0 | `\x1b[30m` | Background |

In Synchronet `\x01` (Ctrl-A) color codes: `\x01h\x01m` = bright magenta,
`\x01h\x01r` = hot pink, `\x01h\x01y` = bright yellow.

**Synchronet Classic — header (`text/menu/head.msg`)**
- Box borders: `\x01h\x01m` (bright magenta)
- BBS name: `\x01h\x01y` (bright yellow)
- Time/date: `\x01h\x01w` (bright white)
- Labels: `\x01h\x01w` (bright white)
- Values (last on, uptime): `\x01c` (cyan)

**Simple Shell menus (`text/menu/simple/`)**
- Box borders: `\x01h\x01m` (bright magenta)
- BBS name: `\x01h\x01y` (bright yellow)
- Hotkeys: `\x01h\x01y` (bright yellow)
- Menu text: `\x01h\x01w` (bright white)
- Box background: `\x015` (magenta)

## Security

### Hardening Applied
- AWS Security Group: port 22 (OS SSH) restricted to sysop IP only
- OS SSH: password authentication disabled (key-only)
- `ufw` enabled with default-deny inbound, rate limiting on port 443
- `fail2ban` running with four jails: `sshd`, `sbbs-passwd`, `sbbs-scanner`, `sbbs-shadow`
- Synchronet login throttling (`ctrl/sbbs.ini`):
  - Delay between attempts: 5s; per-attempt throttle: 2s
  - Hack threshold: 5 attempts
  - Temp ban: after 20 attempts, 15 min duration
  - Permanent filter: after 50 attempts, 24h duration
- IP blocklist: `text/ip-silent.can` — connections silently dropped before Synchronet wakes up

### Logs

| File | Contents |
|------|----------|
| `/sbbs/data/logs/MMDDYY.log` | Daily BBS activity (logins, sessions, events) |
| `/sbbs/data/logs/MMDDYY.lol` | Daily session summary (user, node, times, stats) |
| `/sbbs/data/hack.log` | HTTP/HTTPS hack attempts (path traversal, `/bin/sh`, etc.) |
| `/sbbs/data/hungup.log` | Users who disconnected mid-session |

### The Jamaican

Shortly after the BBS went live, `34.212.124.156` (`ec2-34-212-124-156.us-west-2.compute.amazonaws.com`) opened a number simultaneous HTTPS connections in a single second, probing for weak TLS (SSLv2, TLSv1.0, TLSv1.1). Synchronet rejected all of them: no downgrade was possible. Seems like a kid with an AWS account and a TLS scanner.  I misstyped the IP in my intial recon and geolocated to Jamaica and the name stuck. The IP has been reported on [https://www.abuseipdb.com/](https://www.abuseipdb.com/check/34.212.124.156).

```
3/17 17:56:34 web  0044 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 35815
3/17 17:56:34 web  0045 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 25147
3/17 17:56:34 web  0046 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 33376
3/17 17:56:34 web  0044 TLS WARNING 'Server sent handshake for the obsolete SSLv2 protocol' (-13) setting session active
3/17 17:56:34 web  0046 TLS WARNING 'Invalid version number 3.1, should be at least 3.3' (-32) setting session active
3/17 17:56:34 web  0050 TLS info 'No encryption mechanism compatible with the remote system could be found' (-20) setting session active
```

IP added to `text/ip-silent.can`. Connections now dropped silently before Synchronet wakes up.

## The Pelican

The Pelican is the BBS chat bot: a sassy southern coastal Peli-hen who knows her way around a terminal. Powered by the Claude API (Haiku model).

**1-on-1 chat** (`mods/pelican.js`): accessible via the 'T' key in both shells. Maintains per-user conversation history across sessions in `data/user/pelican_NNNN.json`. Config (API key, model, token limits) in `ctrl/pelican.ini` (gitignored).

**Multinode chat** (`mods/multichat_pelican.js`): a full JS reimplementation of Synchronet's built-in multinode chat that layers in Pelican responses. She chimes in when addressed by name (`pelican` / `peli`) or when there are 3 or fewer users in the channel. Shared channel history in `data/user/pelican_chan.json`.

## Logon Splash Art

At logon, `mods/logon.js` displays a random piece of ANSI art chosen based on the user's terminal width:

- **>80 columns** — a random `random_wide*` file is served via `cat` (using `EX_STDIO | EX_NATIVE` so the raw bytes pass through unmodified)
- **≤80 columns** (e.g. SyncTERM, standard 80-col terminals) — a random `random_narrow*` file is served via `bbs.menu()`

Art files live in `text/menu/` and deploy to `/sbbs/text/menu/` via rsync:

| File | Type |
|------|------|
| `random_narrow_closeup02.ans` | Narrow |
| `random_narrow_logo.ans` | Narrow |
| `random_wide_1XXXX.ans` | Wide |
| `random_wide_XXXXX.ans` | Wide |
| `random_wide_closeup.ans` | Wide |

Source art files (pre-rename) are in `art/`. To add more, drop a file matching `random_wide*` or `random_narrow*` into `text/menu/` and rsync to deploy — the logon module picks from all matching files at random.

## Sysop

foodbark (Benjamin Hausmann): send feedback from inside the BBS or open an issue here.

## Contributing

This is a community BBS for a hacker con. If you want to help:
- Open an issue or PR
- Or just connect to the BBS and leave feedback via the message boards I will try to watch them.
