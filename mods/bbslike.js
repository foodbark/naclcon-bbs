// bbslike.js
//
// foodbark BBS — "BBSes We Like": a curated menu of hand-picked BBSes
// reachable directly from within foodbark BBS via Synchronet's telnet gateway.
// SSH-only BBSes are displayed with the external connect command since
// Synchronet has no outbound SSH client.

"use strict";

require("sbbsdefs.js", "P_NOERROR");

// Refuse to run outside a real node session. This module is an interactive
// door invoked via xtrn.ini (`cmd=*bbslike`); if it's ever launched under
// jsexec with no user attached, `console.getnum()` returns on EOF forever
// and the loop burns a CPU core. Guard by requiring a node context.
if (typeof bbs === "undefined" || !bbs.node_num) {
	log(LOG_WARNING, "bbslike: refusing to run outside a node session");
	exit(1);
}

// Edit this array to curate the list. Keep it short; this is NOT a federated
// BBS directory, it's a sysop's hand-picked honor roll.
//
// Pepper Quest is the odd one out: an Evennia MUD rather than a BBS, written
// by a friend of the sysop at Pepper Con. It's here as well as in the Arcade
// because it's worth pointing people at from both places. `note` is optional
// and only exists to flag that kind of exception in the menu.
var bbses = [
	{ name: "20 for Beers",      host: "20forbeers.com",          port: 23,   protocol: "telnet" },
	{ name: "ACiD Underworld",   host: "blackflag.acid.org",      port: 23,   protocol: "telnet" },
	{ name: "Bottomless Abyss",  host: "bbs.bottomlessabyss.net", port: 2222, protocol: "ssh"    },
	{ name: "Al's Geek Lab",     host: "bbs.alsgeeklab.com",      port: 2323, protocol: "telnet" },
	{ name: "Telehack",          host: "telehack.com",            port: 23,   protocol: "telnet" },
	{ name: "Particles! BBS",    host: "particlesbbs.dyndns.org", port: 6400, protocol: "telnet" },
	{ name: "Pepper Quest",      host: "pq4.peppercon.games",     port: 4000, protocol: "telnet",
	  note: "MUD" },
];

function connect_string(b) {
	if (b.protocol == "telnet")
		return "telnet " + b.host + (b.port != 23 ? " -p " + b.port : "");
	return "ssh " + b.host + " -p " + b.port;
}

function show_menu() {
	console.clear(LIGHTGRAY);
	console.print("\x01n\x01h\x01r===============================================================================\x01n\r\n");
	console.print("\r\n");
	console.print("\x01n\x01h\x01m                   __                 _ _                _\x01n\r\n");
	console.print("\x01n\x01h\x01m                  / _\xb3 ___   ___   __\xb3 \xb3 \xb3__   __ _ _ __\xb3 \xb3 __\x01n\r\n");
	console.print("\x01n\x01h\x01m                 \xb3 \xb3_ / _ \\ / _ \\ / _` \xb3 '_ \\ / _` \xb3 '__\xb3 \xb3/ /\x01n\r\n");
	console.print("\x01n\x01h\x01m                 \xb3  _\xb3 (_) \xb3 (_) \xb3 (_\xb3 \xb3 \xb3_) \xb3 (_\xb3 \xb3 \xb3  \xb3   <\x01n\r\n");
	console.print("\x01n\x01h\x01m                 \xb3_\xb3  \\___/ \\___/ \\__,_\xb3_.__/ \\__,_\xb3_\xb3  \xb3_\xb3\\_\\\x01n\r\n");
	console.print("\r\n");
	console.print("\x01n\x01h\x01y                          B B S e s   W e   L i k e                            \x01n\r\n");
	console.print("\x01n\x01h\x01r-------------------------------------------------------------------------------\x01n\r\n");
	console.print("\r\n");
	for (var i = 0; i < bbses.length; i++) {
		var b = bbses[i];
		console.print(format("\x01n\x01h\x01y %2d\x01n\x01w  %-22s  \x01h\x01k%s%s\x01n\r\n",
			i + 1, b.name, connect_string(b),
			b.note ? "  \x01h\x01m(" + b.note + ")" : ""));
	}
	console.print("\r\n");
	console.print("\x01n\x01h\x01k  Hit Ctrl-] during a session for the gateway menu (disconnect/back).\x01n\r\n");
	console.print("\r\n");
	console.mnemonics("\x01n\x01wEnter number or [\x01h\x01yQ\x01n\x01wuit]: ");
}

while (bbs.online && !js.terminated) {
	show_menu();
	var n = console.getnum(bbses.length);
	if (n < 1) break;
	var b = bbses[n - 1];
	console.clear(LIGHTGRAY);

	if (b.protocol == "telnet") {
		log("bbslike: connecting to " + b.name + " (" + b.host + ":" + b.port + ")");
		bbs.exec("?telgate " + b.host + ":" + b.port);
	} else {
		// Synchronet has no outbound SSH. Show the user how to connect externally.
		console.print("\x01n\x01h\x01y" + b.name + " is SSH-only.\x01n\r\n\r\n");
		console.print("\x01n\x01wConnect from your own terminal (SyncTERM, OpenSSH, PuTTY, etc.):\r\n\r\n");
		console.print("\x01h\x01g   " + connect_string(b) + "\x01n\r\n\r\n");
		console.print("\x01n\x01h\x01k(Synchronet doesn't ship an outbound SSH client, so we can't\r\n");
		console.print(" bridge this one from inside the BBS. Sorry.)\x01n\r\n\r\n");
		console.pause();
	}
}

console.clear(LIGHTGRAY);
