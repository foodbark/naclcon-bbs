# NaClCON BBS

Official bulletin board for [NaClCON 2026](https://naclcon.com) — the hacker conference on the coast of Carolina Beach, NC. May 31 - June 2, 2026.

> Play Hard. Hack Harder.

## Connect

```sh
ssh -p 2222 <yourname>@34.229.165.250
```

New users can register on connect. No invite needed.

## What This Is

A Synchronet BBS (v3.21) running on AWS EC2 (Ubuntu 24.04). Spun up as a community hub for NaClCON attendees — message boards, file areas, chat, doors, and The Guru.

This repo tracks the NaClCON-specific configuration, branding, and customizations layered on top of a stock Synchronet install. It is a work in progress. If you know Synchronet, BBS culture, or just want to break things constructively — PRs welcome.

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
- [x] Local message boards + DOVE-Net (global Synchronet network)
- [x] Chat, file areas, external doors
- [x] Security hardening (see below)
- [ ] CTF-related content
- [ ] Custom doors / programs
- [ ] Con schedule / info in bulletins
- [ ] ANSI art splash screens

## Security

### Hardening Applied
- AWS Security Group: port 22 (OS SSH) restricted to sysop IP only
- `ufw` enabled with default-deny inbound, rate limiting on ports 443 and 2222
- Synchronet login throttling tightened (hack threshold: 5, temp ban: 1h, auto-filter after 25 attempts)

### The Jamaican

Shortly after the BBS went live, `34.212.124.156` (`ec2-34-212-124-156.us-west-2.compute.amazonaws.com`) opened 7 simultaneous HTTPS connections in a single second, probing for weak TLS (SSLv2, TLSv1.0, TLSv1.1). Synchronet rejected all of them — no downgrade was possible. Classic script kiddie with an AWS account and a TLS scanner.

```
3/17 17:56:34 web  0044 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 35815
3/17 17:56:34 web  0045 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 25147
3/17 17:56:34 web  0046 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 33376
3/17 17:56:34 web  0044 TLS WARNING 'Server sent handshake for the obsolete SSLv2 protocol' (-13) setting session active
3/17 17:56:34 web  0046 TLS WARNING 'Invalid version number 3.1, should be at least 3.3' (-32) setting session active
3/17 17:56:34 web  0050 TLS info 'No encryption mechanism compatible with the remote system could be found' (-20) setting session active
```

IP added to `text/ip-silent.can`. Connections now dropped silently before Synchronet wakes up.

## Sysop

foodbark (Benjamin Hausmann) — send feedback from inside the BBS or open an issue here.

## Contributing

This is a community BBS for a hacker con. If you want to help:
- Open an issue or PR
- Or just connect to the BBS and leave feedback via the message boards
