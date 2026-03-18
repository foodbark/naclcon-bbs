# NaClCON BBS

Official bulletin board for [NaClCON 2026](https://naclcon.com) hacker conference in Carolina Beach, NC. May 31 - June 2, 2026.

> Play Hard. Hack Harder.

## Connect

```sh
ssh -p 2222 <yourname>@34.229.165.250
```

New users can register on connect. No invite needed.

## What This Is

A Synchronet BBS (v3.21) running on AWS EC2 (Ubuntu 24.04). Spun up as a community hub for NaClCON attendees — message boards, file areas, chat, doors, and The Pelican.

This repo tracks the NaClCON-specific configuration, branding, and customizations layered on top of a stock Synchronet install. It is a work in progress. If you know Synchronet, BBS culture, or just want to break things constructively PRs are welcome.

## Repo Structure

```
ctrl/           # Synchronet config (sbbs.ini, main.ini, modopts.ini, etc.)
text/           # Display files, banners, filter lists
text/menu/      # Menu screens (head, logon, simple shell)
mods/exec/      # JS module overrides (takes precedence over exec/)
data/msgs/      # Auto-message shown at logon
```

## Status

- [x] SSH access on port 2222
- [x] New user registration
- [x] NaClCON branding throughout
- [x] Local message boards
- [x] Chat, file areas, external doors
- [x] Security hardening (see below)
- [x] Shell restricted to Synchronet Classic + Deuce's Lightbar Shell
- [x] NaClCON color palette applied to both shells
- [ ] CTF-related content
- [ ] Custom doors / programs
- [ ] Con schedule / info in bulletins
- [ ] ANSI art splash screens
- [ ] The Pelican — upgrade from guru.dat pattern matching to Claude API (see below)

## Color Palette

Derived from [naclcon.com](https://naclcon.com).

| Role | Web hex | ANSI 16-color | Ctrl-A / attr |
|---|---|---|---|
| Background | `#1F1346` (deep purple) | Black (0) | `\x010` / `0x0_` |
| Bar / box background | `#2f1c6a` → magenta | Magenta bg (5) | `\x015` / `0x5_` |
| Primary text | white | Bright white (F) | `\x01h\x01w` / `0x5F` |
| BBS name / hotkeys | `#8c85ff` → yellow | Bright yellow (E) | `\x01h\x01y` |
| Box borders | `#673de6` → magenta | Bright magenta (D) | `\x01h\x01m` / `0x0D` |
| Info labels | white | White (7) | `\x01w` |
| Info values / secondary | teal `#00b090` → cyan | Cyan (3) / Bright cyan (B) | `\x01c` / `\x01h\x01c` |
| Command prompt | — | Bright magenta (D) | `0x0D` |

### Where each shell uses these

**Deuce's Lightbar Shell (`mods/exec/lbshell.js`)**
- Top bar: `0x5F` (bright white on magenta)
- Status bar row 1: `0x5F` — NaClCON BBS, time, node, uptime
- Status bar row 2: `0x5B` (bright cyan on magenta) — last on, calls, since
- Content area: `0x07` (white on black)
- Command prompt: `0x0D` (bright magenta)

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
- `ufw` enabled with default-deny inbound, rate limiting on ports 443 and 2222
- Synchronet login throttling tightened (hack threshold: 5, temp ban: 1h, auto-filter after 25 attempts)

### The Jamaican

Shortly after the BBS went live, `34.212.124.156` (`ec2-34-212-124-156.us-west-2.compute.amazonaws.com`) opened a number simultaneous HTTPS connections in a single second, probing for weak TLS (SSLv2, TLSv1.0, TLSv1.1). Synchronet rejected all of them: no downgrade was possible. Seems like a kid with an AWS account and a TLS scanner.  I misstyped the IP in my intial recon and and geolocated to Jamaica, and the name stuck. The IP has been reported on[https://www.abuseipdb.com/](https://www.abuseipdb.com/check/34.212.124.156).

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

The Pelican is the BBS chat Bot — a sassy southern coastal Peli-hen who knows her way around a terminal. Currently powered by `ctrl/guru.dat` pattern matching (classic Synchronet guru chat).

**Planned upgrade**: replace guru.dat with a Synchronet JS module that calls the Claude API, maintaining full conversation context and The Pelican's persona via system prompt. Cost at BBS-scale traffic: a few dollars for the entire con weekend.

System prompt concept:
```
You are The Pelican, the AI chat assistant for NaClCON BBS — the hacker
conference in Carolina Beach, NC. You are a sassy, warm southern coastal
lady. You say things like "hun", "darlin'", "sugar", "sweetie", and
"bless your heart". You occasionally *squawk* like a pelican. You know
your way around a terminal, are seasonally local to Carolina Beach
(a snowbird?), and have opinions about hacker culture, the
beach, and good seafood. Keep responses short — this is a BBS, not a
novel. Never break character.
```

## Sysop

foodbark (Benjamin Hausmann) — send feedback from inside the BBS or open an issue here.

## Contributing

This is a community BBS for a hacker con. If you want to help:
- Open an issue or PR
- Or just connect to the BBS and leave feedback via the message boards I will try to watch them.
