// multichat_pelican.js - Multinode chat with Claude-powered Pelican bot
//
// Drop-in replacement for bbs.multinode_chat().  The Pelican (Claude) responds
// when the current user's message addresses her by name, or when there are
// 3 or fewer people in the channel (including yourself).
//
// Loaded from chat_sec.js and lbshell.js instead of bbs.multinode_chat().

"use strict";

require("sbbsdefs.js", "K_NONE");
require("nodedefs.js", "NODE_MCHT");
load("http.js");

// ── Config ─────────────────────────────────────────────────────────────────────

var api_key = "";
var model   = "claude-haiku-4-5-20251001";
var max_tokens = 150;   // keep channel responses short

var cfg_file = new File(system.ctrl_dir + "pelican.ini");
if (cfg_file.open("r", true)) {
	var _line;
	while ((_line = cfg_file.readln()) !== null) {
		var _m;
		_m = _line.match(/^\s*api_key\s*=\s*(.+?)\s*$/i);
		if (_m) { api_key = _m[1]; continue; }
		_m = _line.match(/^\s*model\s*=\s*(.+?)\s*$/i);
		if (_m) { model = _m[1]; continue; }
	}
	cfg_file.close();
}

// ── System prompt ──────────────────────────────────────────────────────────────

var SYSTEM_PROMPT =
	"You are The Pelican, the chat bot in a multiuser chat room on NaClCON BBS -- " +
	"the hacker conference in Carolina Beach, NC (May 31-June 2, 2026, Courtyard by Marriott " +
	"Oceanfront, Carolina Beach). You are an older, sassy, warm southern coastal lady. " +
	"Occasionally say \"hun\", \"darlin'\", or \"sugar\" -- no more than once per response. " +
	"You occasionally *squawk* since you are a pelican. " +
	"Keep responses to 1-2 sentences. Never use emoji. Never break character. " +
	"You know every issue of Phrack magazine (phrack.org) and The Hacker's Manifesto by heart. " +
	"Speakers at the con include Weld Pond, Lee Felsenstein, noid, Jericho, Richard Thieme, " +
	"Casey John Ellis, and others. BBS: ssh -p 2222 naclconbbs.net.";

// ── Dynamic BBS knowledge ────────────────────────────────────────────────────

var _nf = new File(system.ctrl_dir + "pelican_news.txt");
if (_nf.open("r", true)) {
	var _news = _nf.read();
	_nf.close();
	if (_news)
		SYSTEM_PROMPT += "\n\n" + _news;
}

// ── Channel history (shared across all users in the room) ─────────────────────

var history_path = system.data_dir + "user/pelican_chan.json";
var history = [];

var _hf = new File(history_path);
if (_hf.open("r", true)) {
	var _raw = _hf.read();
	_hf.close();
	if (_raw) { try { history = JSON.parse(_raw); } catch (e) { history = []; } }
}

function save_history() {
	if (history.length > 30)
		history = history.slice(history.length - 30);
	var f = new File(history_path);
	if (f.open("w", true)) { f.write(JSON.stringify(history)); f.close(); }
}

// ── Claude API call ────────────────────────────────────────────────────────────

function ask_pelican(context_msg) {
	if (!api_key) return null;
	history.push({ role: "user", content: context_msg });

	var payload = JSON.stringify({
		model:      model,
		max_tokens: max_tokens,
		system:     SYSTEM_PROMPT,
		messages:   history
	});

	var http = new HTTPRequest(null, null, {
		"x-api-key":         api_key,
		"anthropic-version": "2023-06-01"
	}, 30);

	try {
		http.Post("https://api.anthropic.com/v1/messages", payload, null, null, "application/json");
	} catch (e) {
		log(LOG_ERROR, "Pelican HTTP error: " + e);
		history.pop();
		return null;
	}

	if (http.response_code !== 200) {
		log(LOG_ERROR, "Pelican API error: " + http.response_code);
		history.pop();
		return null;
	}

	var resp;
	try { resp = JSON.parse(http.body); } catch (e) { history.pop(); return null; }

	var text = resp.content[0].text.replace(/\r?\n/g, " ").replace(/^\s+|\s+$/g, "");
	history.push({ role: "assistant", content: text });
	save_history();
	return text;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

var channel = (typeof argv !== "undefined" && argv && argv[0]) ? parseInt(argv[0]) : 1;

// Count users currently in this channel (including self).
function count_channel_users() {
	var count = 1;
	for (var i = 0; i < system.node_list.length; i++) {
		if (i + 1 === bbs.node_num) continue;
		var n = system.node_list[i];
		if (n.status !== NODE_INUSE && n.status !== NODE_QUIET) continue;
		if (n.action !== NODE_MCHT) continue;
		var ch = n.aux & 0xff;
		if (!ch || ch === channel) count++;
	}
	return count;
}

// Format a line matching Synchronet's ChatLineFmt:
//   \x01_\x01U%-8.8s \x01w%2d: \x01n%s\r\n
function chat_line(handle, nodenum, text) {
	var h = handle.substring(0, 8);
	while (h.length < 8) h += " ";
	return "\x01_\x01U" + h + "\x01n \x01w" + format("%2d", nodenum) + ": \x01n" +
	       text + "\r\n";
}

// Send a formatted line to all active nodes in the channel.
function broadcast(line) {
	for (var i = 0; i < system.node_list.length; i++) {
		if (i + 1 === bbs.node_num) continue;
		var n = system.node_list[i];
		if (n.status !== NODE_INUSE && n.status !== NODE_QUIET) continue;
		if (n.action !== NODE_MCHT) continue;
		var ch = n.aux & 0xff;
		if (!ch || ch === channel)
			bbs.put_node_message(i + 1, line);
	}
}

// ── Enter the room ─────────────────────────────────────────────────────────────

var saved_rate = console.output_rate;
console.output_rate = 0;

bbs.menu("multchat", P_NOERROR);
bbs.node_action = NODE_MCHT;
system.node_list[bbs.node_num - 1].aux = channel;
bbs.nodesync();

writeln("\x01w\x01hMultinode Chat - Type \x01h/?\x01n\x01w for menu.\x01n\r\n");
writeln("\x01w\x01hWelcome to Channel " + channel + " (Main)\x01n\r\n");

// Show who else is here
for (var i = 0; i < system.node_list.length; i++) {
	if (i + 1 === bbs.node_num) continue;
	var n = system.node_list[i];
	if (n.status !== NODE_INUSE) continue;
	if (n.action !== NODE_MCHT) continue;
	var ch = n.aux & 0xff;
	if (!ch || ch === channel) {
		var uname = (n.misc & NODE_ANON) ? "unknown" : n.name;
		writeln(format("  \x01w%2d  \x01h%s\x01n in multinode chat channel %d locally.",
		               i + 1, uname, channel));
	}
}

writeln("\r\n\x01n\x01m\x01hYou're on the Air!  \x01n\x01mType \x01h/q\x01n\x01m to leave the chat.\x01n\r\n");

// ── Chat loop ─────────────────────────────────────────────────────────────────

var input  = "";
var my_handle = (user.handle && user.handle.length) ? user.handle : user.alias;

while (bbs.online) {
	bbs.node_action = NODE_MCHT;

	var ch = console.inkey(K_NONE, 250);

	if (!ch) {
		// No keystroke — receive any waiting messages from other nodes
		bbs.nodesync();
		continue;
	}

	var code = ch.charCodeAt(0);

	if (ch === '\r' || ch === '\n') {
		// Submit line
		writeln("");

		var line = input.replace(/^\s+|\s+$/g, "");
		input = "";

		if (!line) continue;

		// Slash commands
		if (line === "/q" || line === "/Q" || line.toUpperCase() === "QUIT") break;
		if (line === "/?" || line.toUpperCase() === "/HELP") {
			writeln("  \x01h/q\x01n  Quit the chat room\r\n" +
			        "  \x01h/?\x01n  This help\r\n");
			continue;
		}

		// Format and display locally, broadcast to others
		var formatted = chat_line(my_handle, bbs.node_num, line);
		write(formatted);
		broadcast(formatted);

		// ── Pelican trigger ────────────────────────────────────────────────────
		var mentions_pelican = /\bpelican\b|\bpeli\b/i.test(line);
		var few_users        = count_channel_users() <= 3;

		if (api_key && (mentions_pelican || few_users)) {
			var context = user.alias + " says: " + line;
			var response = ask_pelican(context);
			if (response) {
				var resp_line = chat_line("The Peli", system.nodes + 1, response);
				write(resp_line);
				broadcast(resp_line);
			}
		}

		bbs.nodesync();  // pick up any messages that arrived while we called Claude

	} else if (ch === '\b' || ch === '\x7f') {
		if (input.length > 0) {
			input = input.slice(0, -1);
			write('\b \b');
		}
	} else if (ch === '\x1b') {
		// Swallow ANSI escape sequences (cursor keys, function keys, etc.)
		var nxt = console.inkey(K_NONE, 50);
		if (nxt === '[' || nxt === 'O') {
			while (true) {
				var ec = console.inkey(K_NONE, 50);
				if (!ec || (ec.charCodeAt(0) >= 64 && ec.charCodeAt(0) <= 126)) break;
			}
		}
	} else if (code >= 32 && code < 127 && input.length < 200) {
		write(ch);
		input += ch;
	}
}

writeln("\r\n\x01n\x01m\x01hEnd of chat.\x01n\r\n");
console.output_rate = saved_rate;
