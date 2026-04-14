NACLCON 2026 BBS - SYSOP MANUAL

SYSTEM DETAILS
==============
BBS Name: NaClCON BBS
Location: Carolina Beach, NC
Host: AWS EC2 (Ubuntu 24.04.4 LTS)
Sysop: foodbark

SECURITY & INCIDENT RESPONSE
============================

--- The Jamaican (34.212.124.156) ---
An AWS EC2 instance (us-west-2 / Oregon) running an automated TLS scanner.
Not actually Jamaican. Just a script kiddie with a cloud account.

First observed: 2026-03-17 17:56:34
Activity: Opened 7 simultaneous HTTPS connections in the same second, probing
for weak TLS versions (SSLv2, TLSv1.0, TLSv1.1). Synchronet rejected all of
them correctly -- no encryption downgrade was possible.

Log evidence:
  3/17 17:56:34 web  0044 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 35815
  3/17 17:56:34 web  0045 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 25147
  3/17 17:56:34 web  0046 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 33376
  3/17 17:56:34 web  0047 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 28278
  3/17 17:56:34 web  0048 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 63196
  3/17 17:56:34 web  0049 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 15008
  3/17 17:56:34 web  0050 HTTPS [34.212.124.156] Connection accepted on 172.31.24.94 port 443 from port 17137
  3/17 17:56:34 web  0044 TLS WARNING 'Server sent handshake for the obsolete SSLv2 protocol' (-13) setting session active
  3/17 17:56:34 web  0046 TLS WARNING 'Invalid version number 3.1, should be at least 3.3' (-32) setting session active
  3/17 17:56:34 web  0047 TLS WARNING 'Invalid version number 3.2, should be at least 3.3' (-32) setting session active
  3/17 17:56:34 web  0050 TLS info 'No encryption mechanism compatible with the remote system could be found' (-20) setting session active

Mitigations applied (2026-03-17):
  - IP added to text/ip-silent.can (Synchronet silently drops connections)
  - ufw rate limiting enabled on port 443 (>6 connections/30s = blocked)

CRITICAL FIXES
==============
1. TLS KEY ERROR: Rename /sbbs/ctrl/cryptlib.key to .bak
   to force regeneration.
2. PORT BINDING: Use 'setcap' on the sbbs binary to
   allow ports < 1024.
3. BAJA SHELLS: If you get "ERROR opening *.bin", the Baja source files
   need to be compiled. Run: cd /sbbs/exec && for f in *.src; do baja "$f"; done

HARDENING APPLIED
=================
- AWS Security Group: Port 22 restricted to sysop IP only
- OS SSH: password authentication disabled (key-only)
- ufw enabled (default deny inbound) with rate limiting on 443 and 2222
- fail2ban running with four jails: sshd, sbbs-passwd, sbbs-scanner, sbbs-shadow
- Synchronet login throttling: 5s delay between attempts, hack threshold 5,
  temp ban after 20 attempts (15 min), permanent filter after 50 attempts (24h)

SYSOP QUICK REF
===============
Sysop Menu: [!]
Remote Command: [;]
Security: Level 99 / Flags A-Z
