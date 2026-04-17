# NaClCON BBS

Semi-official bulletin board system for [NaClCON 2026](https://naclcon.com) hacker conference in Carolina Beach, NC. May 31 - June 2, 2026.

> Play Hard. Hack Harder.

## Connect

```
ssh naclconbbs.net -p 2222
```

```
telnet naclconbbs.net
```

## Server

A Synchronet BBS (v3.21) running on AWS EC2 (Ubuntu 24.04). Spun up as a community hub for NaClCON attendees: message boards, file areas, chat, doors, and The Pelican.

- **Nodes**: 20 (supports 20 concurrent users), currently on a t3.medium
- **Sysop**: foodbark

## AWS Security Group — Required Open Ports

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 22 | TCP | OS SSH | Restrict to sysop IP only |
| 23 | TCP | Telnet (public) | Open to all |
| 2222 | TCP | BBS SSH (public) | Open to all |
| 80 | TCP | HTTP | Open to all |
| 443 | TCP | HTTPS | Open to all |
| 1123 | TCP | WebSocket | Open to all |
| 11235 | TCP | WebSocket TLS | Open to all |

> FTP (21), Gopher (70), and NNTP (119) are configured but currently disabled.
> To re-enable: set `AutoStart = true` (FTP, `ctrl/sbbs.ini`) or `Enabled=false` → `true`
> (Gopher/NNTP, `ctrl/services.ini`), then open the corresponding port in the Security Group.

## Status

- [x] SSH access on port 2222
- [x] Telnet access on port 23
- [x] New user registration
- [x] NaClCON branding throughout
- [x] Local message boards
- [x] Chat, file areas, external doors
- [x] Security hardening (see below)
- [x] Shell restricted to Synchronet Classic + Deuce's Lightbar Shell
- [x] NaClCON color palette applied to both shells
- [x] The Pelican — Claude-powered AI chat bot (1-on-1 and multinode)
- [x] Speaker list bulletin and per-speaker message threads
- [x] Pre-login NaClCON banner shown at connect (before login prompt, via `mods/login.js`)
- [x] Terminal-adaptive splash art at logon (wide ANSI art for large terminals >80 col, narrow art for 80-col terminals like SyncTERM; see `mods/logon.js`)
- [ ] CTF-related content
- [ ] Custom doors / programs
- [ ] Browser terminal (fTelnet): wire into webv4 so users can connect from a browser without an SSH client

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

### The Jamaican

Shortly after the BBS went live, `34.212.124.156` (`ec2-34-212-124-156.us-west-2.compute.amazonaws.com`) opened a number of simultaneous HTTPS connections in a single second, probing for weak TLS (SSLv2, TLSv1.0, TLSv1.1). Synchronet rejected all of them: no downgrade was possible. Seems like a scriptkiddy with an AWS account and a TLS scanner. I fat-fingered the IP in my initial recon and geolocated to Jamaica. The IP has been reported on [abuseipdb.com](https://www.abuseipdb.com/check/34.212.124.156).

```
3/17 17:56:34 web  0044 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 35815
3/17 17:56:34 web  0045 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 25147
3/17 17:56:34 web  0046 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 33376
3/17 17:56:34 web  0044 TLS WARNING 'Server sent handshake for the obsolete SSLv2 protocol' (-13) setting session active
3/17 17:56:34 web  0046 TLS WARNING 'Invalid version number 3.1, should be at least 3.3' (-32) setting session active
3/17 17:56:34 web  0050 TLS info 'No encryption mechanism compatible with the remote system could be found' (-20) setting session active
```

IP added to `text/ip-silent.can`. Connections now dropped silently before Synchronet wakes up.

Of course, this incident was followed by significant system hardening.

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

### fail2ban

Four jails are active, configured in `/etc/fail2ban/jail.d/sbbs.conf`:

| Jail | Watches | Trigger | Ban |
|------|---------|---------|-----|
| `sshd` | `/var/log/auth.log` | OS SSH brute force (default Debian config) | default |
| `sbbs-passwd` | `/sbbs/data/hack.log` | HTTP request for `/etc/passwd` | 1 hit → 1hr |
| `sbbs-shadow` | `/sbbs/data/hack.log` | HTTP request for `/etc/shadow` | 1 hit → 24hr |
| `sbbs-scanner` | `/sbbs/data/hack.log` | Any other web path traversal outside web root | 3 hits/week → 24hr |

The three `sbbs-*` jails key off Synchronet's `hack.log`, which records all HTTP requests that escape the web root. Filters are in `/etc/fail2ban/filter.d/sbbs-{passwd,shadow,scanner}.conf`.

The idea is slap on the wrist for looking around, harder slap if you are after /etc/shadow, full ban if you are trying to bruteforce the OS.

### Logs

To stay on top of activity without being logged into the server, all logs are synced off-box to S3 every minute via `/home/ubuntu/bin/s3_log_sync.sh` (cron). S3 bucket: `s3://naclcon-bbs-dead-drop/`. BBS logs land in `bbs-logs/`, system logs in `system-logs/<hostname>/`. An Elastic Stack instance on a separate EC2 ingests from S3 for dashboards and alerting.

| File | Contents |
|------|----------|
| `/sbbs/data/logs/MMDDYY.log` | Daily BBS activity (logins, sessions, file transfers, events) |
| `/sbbs/data/logs/MMDDYY.lol` | Daily session summary (user, node, times, stats) |
| `/sbbs/data/logs/http-MMDDYY.log` | HTTP access log (one line per web request) |
| `/sbbs/data/hack.log` | HTTP/HTTPS hack attempts (path traversal, `/bin/sh`, etc.) |
| `/sbbs/data/hungup.log` | Users who disconnected mid-session |
| `/var/log/auth.log` | OS SSH logins, sudo, PAM authentication |
| `/var/log/ufw.log` | Firewall blocks and allows |
| `/var/log/fail2ban.log` | Brute-force attempts and bans |
| `/var/log/syslog` | General OS events |

Log verbosity: the terminal server (`[BBS]`) logs at `Debugging` level to capture file transfer details. All other servers (Web, Services) log at `Info`.

### SSH Login Behavior (SSH_ANYAUTH)

`SSH_ANYAUTH` is currently enabled in `ctrl/sbbs.ini`. This makes the SSH server accept any credentials without checking them, which means every user, new and returning, goes through the full BBS login sequence (username/password prompt + logon screens).

**Before this change:** `ssh username@host -p 2222` auto-logged returning users in at the SSH layer. No BBS login prompt.

**Why it was added:** New users connecting via SSH were being rejected before reaching the BBS because their SSH clients weren't sending credentials the server would accept.

**Trade-off:** New user signup works reliably. Returning users have a clunkier experience (no fast logon).

**TODO:** Figure out the root cause of the new-login failures without `SSH_ANYAUTH`, then revert. Returning users with BBS credentials provided at the SSH level (or SSH pubkeys registered in their BBS account) should auto-login without it.

## The Pelican

The Pelican is the BBS chat bot: a sassy southern coastal Peli-hen who knows her way around a terminal. Powered by the Claude API (Haiku model). Best experienced in SyncTERM (syncterm.bbsdev.net).

**1-on-1 chat** (`mods/pelican.js`): accessible via the 'T' key in both shells. Maintains per-user conversation history across sessions in `data/user/pelican_NNNN.json`. Config (API key, model, token limits) in `ctrl/pelican.ini` (gitignored). In private chat she gives longer, lore-heavy responses (3-5 sentences) and wraps text to your terminal width.

**Multinode chat** (`mods/multichat_pelican.js`): a full JS reimplementation of Synchronet's built-in multinode chat that layers in Pelican responses. She chimes in when addressed by name (`pelican` / `peli`) or when there are 3 or fewer users in the channel. Shared channel history in `data/user/pelican_chan.json`.

**Persona & knowledge:** She's warm but sassy, drops a "hun" or "darlin'" occasionally (hard cap: one per response, skipped in most). She knows full NaClCON 2026 details (speakers, schedule, venue, tickets). Her canonical texts: every issue of Phrack (phrack.org), The Hacker's Manifesto (The Mentor, 1986, Phrack #7), the DoD Rainbow Series (Orange Book/TCSEC, Password Management Guideline, TCSEC Application Guidance, Computer Security Glossary), and Neuromancer (Gibson, 1984).

## Logon Splash Art

At logon, `mods/logon.js` displays a random piece of ANSI art chosen based on the user's terminal width:

- **>80 columns**  a random `random_wide*` file is served via `cat` (using `EX_STDIO | EX_NATIVE` so the raw bytes pass through unmodified)
- **≤80 columns** (e.g. SyncTERM, standard 80-col terminals) — a random `random_narrow*` file is served via `bbs.menu()`

Art files live in `text/menu/` and deploy to `/sbbs/text/menu/` via rsync:

| File | Type |
|------|------|
| `random_narrow_closeup02.ans` | Narrow |
| `random_narrow_logo.ans` | Narrow |
| `random_wide_1XXXX.ans` | Wide |
| `random_wide_XXXXX.ans` | Wide |
| `random_wide_closeup.ans` | Wide |

Source art files (pre-rename) are in `art/`. To add more, drop a file matching `random_wide*` or `random_narrow*` into `text/menu/` and rsync to deploy. The logon module picks from all matching files at random.

## Sysop

foodbark (Benjamin Hausmann): send feedback from inside the BBS or open an issue here.

## Contributing

This is a community BBS for a hacker con. If you want to help:
- Open an issue or PR
- Or just connect to the BBS and leave feedback via the message boards I will try to watch them.
