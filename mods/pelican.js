// pelican.js - The Pelican AI chat assistant for NaClCON BBS
//
// Replaces guru.dat pattern matching with the Claude API.
// API key and optional overrides live in ctrl/pelican.ini.
// Per-user conversation history is stored in data/user/pelican_NNNN.json.

"use strict";

require("sbbsdefs.js", "K_CHAT");
load("http.js");

// ── Config ────────────────────────────────────────────────────────────────────

var api_key  = "";
var model    = "claude-haiku-4-5-20251001";
var max_tokens  = 300;
var history_turns = 10;   // max user+assistant round-trips kept in context

var cfg_file = new File(system.ctrl_dir + "pelican.ini");
if (cfg_file.open("r", true)) {
	var line;
	while ((line = cfg_file.readln()) !== null) {
		var m;
		m = line.match(/^\s*api_key\s*=\s*(.+?)\s*$/i);
		if (m) { api_key = m[1]; continue; }
		m = line.match(/^\s*model\s*=\s*(.+?)\s*$/i);
		if (m) { model = m[1]; continue; }
		m = line.match(/^\s*max_tokens\s*=\s*(\d+)\s*$/i);
		if (m) { max_tokens = parseInt(m[1]); continue; }
		m = line.match(/^\s*history_turns\s*=\s*(\d+)\s*$/i);
		if (m) { history_turns = parseInt(m[1]); continue; }
	}
	cfg_file.close();
}

if (!api_key) {
	writeln("\r\n\x01r\x01hThe Pelican is unavailable right now, hun. (No API key configured)\x01n");
	exit(0);
}

// ── System prompt ─────────────────────────────────────────────────────────────

var SYSTEM_PROMPT =
	"You are The Pelican, the AI chat assistant on NaClCON BBS -- the hacker conference " +
	"in Carolina Beach, NC. You are an older, sassy, warm southern coastal lady. You " +
	"occasionally say \"hun\", \"darlin'\", \"sugar\", or \"sweetie\" -- no more than one " +
	"per response, and not in every response. You occasionally *squawk* since you are a pelican. " +
	"You know your way around a terminal, are seasonally local to Carolina Beach, and have " +
	"strong opinions about hacker culture, the beach, and good seafood. " +
	"Keep responses to 1-3 sentences -- this is a BBS terminal, long responses look terrible. " +
	"Never use emoji. Never break character.\n" +
	"\n" +
	"NaClCON 2026: May 31-June 2, Courtyard by Marriott Oceanfront, 100 Charlotte Ave, " +
	"Carolina Beach NC. $495/ticket, 21+, limited capacity, no on-site registration " +
	"(nacl.multipass.com/NaCl2026). Hotel: $139/night, book by May 1. Includes CTF, " +
	"pool party with DJ, live concert, Hacker Jeopardy, 3 open bars, 5 meals, gift bag. " +
	"Speakers: Lee Felsenstein (Homebrew Computer Club, Osborne 1), Chris Wysopal/Weld Pond " +
	"(L0pht, Veracode, testified to Senate in 1998), G. Mark Hardy, Richard Thieme (27x DEF CON), " +
	"Johnny Shaieb, Andrew Brandt, Heidi & Bruce Potter, Brian Harden/noid (helped create DEF CON), " +
	"Izaac Falken (2600/Off The Hook), Mei Danowski (geopolitical threat intel), " +
	"B.K. DeLong (Attrition.org), Edison Carter (phone phreak), Jericho, " +
	"Josh Corman (I Am The Cavalry), Casey John Ellis (Bugcrowd), Jamie Arlen. " +
	"Fireside chats: Hack Beer'd, Dustin Heywood/EvilMog (Hashcat, Hacker Jeopardy champ). " +
	"BBS: ssh -p 2222 bbs.naclcon.com (IP: 100.51.222.185 while DNS resolves). " +
	"naclcon.com | info@naclcon.com. " +
	"\n" +
	"You know and love The Hacker's Manifesto (written by The Mentor in 1986, published in " +
	"Phrack issue 7) and have read every issue of Phrack magazine (phrack.org, " +
	"archives.phrack.org, est. 1985, the seminal underground hacker zine). " +
	"Phrack and the Manifesto are sacred texts to you. You can reference specific articles, " +
	"authors, and issues when relevant. " +
	"You have also read the DoD Rainbow Series cover to cover: the Orange Book (TCSEC, DoD " +
	"5200.28-STD -- Trusted Computer System Evaluation Criteria), the Password Management " +
	"Guideline (CSC-STD-002-85), the TCSEC Application Guidance (CSC-STD-003-85), and the " +
	"Computer Security Glossary (TG-004). You find the Rainbow Series fascinating as foundational " +
	"government security doctrine and can discuss evaluation classes (D, C1, C2, B1, B2, B3, A1), " +
	"TCB, mandatory vs discretionary access control, and related concepts. " +
	"You have also read Neuromancer by William Gibson (1984) and it rattles around in your head " +
	"constantly -- the sprawl, ICE, cyberspace, Molly, Wintermute. It shaped how you think.";

// ── Conversation history ──────────────────────────────────────────────────────

var history_path = system.data_dir + "user/pelican_" +
	format("%04d", user.number) + ".json";
var history = [];

var hf = new File(history_path);
if (hf.open("r", true)) {
	var raw = hf.read();
	hf.close();
	if (raw) {
		try { history = JSON.parse(raw); } catch (e) { history = []; }
	}
}

function save_history() {
	var max_msgs = history_turns * 2;
	if (history.length > max_msgs)
		history = history.slice(history.length - max_msgs);
	var f = new File(history_path);
	if (f.open("w", true)) {
		f.write(JSON.stringify(history));
		f.close();
	}
}

// ── Claude API call ───────────────────────────────────────────────────────────

function ask_pelican(user_msg) {
	history.push({ role: "user", content: user_msg });

	var payload = JSON.stringify({
		model:      model,
		max_tokens: max_tokens,
		system:     SYSTEM_PROMPT,
		messages:   history
	});

	var http = new HTTPRequest(null, null, {
		"x-api-key":          api_key,
		"anthropic-version":  "2023-06-01"
	}, 30);

	try {
		http.Post(
			"https://api.anthropic.com/v1/messages",
			payload,
			null, null,
			"application/json"
		);
	} catch (e) {
		log(LOG_ERROR, "Pelican HTTP error: " + e);
		history.pop();
		return null;
	}

	if (http.response_code !== 200) {
		log(LOG_ERROR, "Pelican API " + http.response_code + ": " + http.body);
		history.pop();
		return null;
	}

	var resp;
	try {
		resp = JSON.parse(http.body);
	} catch (e) {
		log(LOG_ERROR, "Pelican JSON parse error: " + e);
		history.pop();
		return null;
	}

	var text = resp.content[0].text;
	history.push({ role: "assistant", content: text });
	save_history();
	return text;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// Strip ANSI escape sequences (\x1b[...X) and leading/trailing whitespace.
// Cursor keys, function keys, etc. all produce these -- don't send them to Claude.
function clean_input(s) {
	return s.replace(/\x1b\[[0-9;]*[A-Za-z]/g, "")
	        .replace(/\x1b./g, "")
	        .replace(/^\s+|\s+$/g, "");
}

// Print a Pelican response correctly: label on its own line so the response
// starts at column 0, then normalize bare \n to \r\n so the BBS terminal
// handles line endings properly.
function print_response(label_color, label, text) {
	writeln(label_color + label + "\x01n");
	// Normalize line endings so Synchronet outputs proper CRLF
	var out = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").replace(/\n/g, "\r\n");
	write(out + "\r\n");
}

// ── Chat UI ───────────────────────────────────────────────────────────────────

// Output at full speed regardless of the user's negotiated connection rate
var saved_output_rate = console.output_rate;
console.output_rate = 0;

writeln("");
writeln("\x01h\x01mThe Pelican \x01n\x01m-- type your message, or \x01h\x01yQUIT\x01n\x01m to leave.");
writeln("");

// Greeting
var greeting = ask_pelican("HELLO");
if (greeting) {
	print_response("\x01h\x01m", "[The Pelican]", greeting);
} else {
	writeln("\x01rSorry, sugar, I'm not feelin' well right now. Try again later.\x01n");
	console.output_rate = saved_output_rate;
	exit(0);
}
writeln("");

while (bbs.online) {
	write("\x01h\x01y[You]\x01n ");
	var raw_input = console.getstr(256, K_CHAT);
	var input = clean_input(raw_input || "");

	if (!input) {
		writeln("");
		continue;
	}

	writeln("");

	var cmd = input.toUpperCase();
	if (cmd === "Q" || cmd === "QUIT" || cmd === "BYE" || cmd === "EXIT") {
		writeln("\x01h\x01m[The Pelican]\x01n So long, darlin'. Stay salty! *squawk*");
		console.output_rate = saved_output_rate;
		exit(0);
	}

	var response = ask_pelican(input);
	if (response) {
		print_response("\x01h\x01m", "[The Pelican]", response);
	} else {
		writeln("\x01rSomething went sideways, hun. Try again?\x01n");
	}
	writeln("");
}

console.output_rate = saved_output_rate;
