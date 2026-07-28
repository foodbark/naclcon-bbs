// pelican.js - The Pelican AI chat assistant for foodbark BBS (terminal)
//
// Replaces guru.dat pattern matching with the Claude API.
// API key and optional overrides live in ctrl/pelican.ini.
// Per-user conversation history is stored in data/user/pelican_NNNN.json.
//
// The persona, the knowledge files, the history handling and the API call all
// live in mods/load/pelican_brain.js, shared with the web chat page at
// webv4/root/api/pelican.ssjs. This file is only the terminal UI.

"use strict";

require("sbbsdefs.js", "K_CHAT");
load(system.mods_dir + "load/pelican_brain.js");

var brain = PelicanBrain;

if (!brain.config.api_key) {
	writeln("\r\n\x01r\x01hThe Pelican is unavailable right now, hun. (No API key configured)\x01n");
	exit(0);
}

var history = brain.load_history(user.number);

function ask_pelican(user_msg) {
	var res = brain.ask(history, user_msg, { venue: "terminal" });
	if (!res.ok) return null;
	history = brain.save_history(user.number, history);
	return res.text;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// Strip ANSI escape sequences (\x1b[...X) and leading/trailing whitespace.
// Cursor keys, function keys, etc. all produce these; don't send them to Claude.
function clean_input(s) {
	return s.replace(/\x1b\[[0-9;]*[A-Za-z]/g, "")
	        .replace(/\x1b./g, "")
	        .replace(/^\s+|\s+$/g, "");
}

var MAX_SESSION = 20;    // API calls per session
var session_count = 0;

function word_wrap(text, width) {
	var lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
	var result = [];
	for (var i = 0; i < lines.length; i++) {
		var line = lines[i];
		while (line.length > width) {
			var cut = width;
			while (cut > 0 && line[cut] !== " ") cut--;
			if (cut === 0) cut = width;
			result.push(line.substring(0, cut));
			line = line.substring(cut).replace(/^ /, "");
		}
		result.push(line);
	}
	return result.join("\r\n");
}

function print_response(label_color, label, text) {
	writeln(label_color + label + "\x01n");
	var width = (console.screen_columns || 80) - 1;
	write(word_wrap(text, width) + "\r\n");
}

// ── Wrapping input ────────────────────────────────────────────────────────────

// Read a line of input, wrapping visually at `width` columns.
// Returns the typed string, or null if the user pressed ESC.
function read_input_wrapped(width) {
	var buf = [];
	var col = 0;

	while (bbs.online) {
		var key = console.getkey(K_NOECHO);
		if (!key) continue;

		var code = key.charCodeAt(0);

		// Submit
		if (key === "\r" || key === "\n") {
			write("\r\n");
			break;
		}

		// ESC = cancel
		if (key === "\x1b") {
			write("\r\n");
			return null;
		}

		// Backspace / DEL
		if (key === "\x08" || key === "\x7f") {
			if (buf.length > 0) {
				buf.pop();
				if (col > 0) {
					write("\x08 \x08");
					col--;
				} else {
					// back up across a wrap point: go up, jump to last column, erase
					write("\x1b[A\x1b[" + width + "G \x1b[" + width + "G");
					col = width - 1;
				}
			}
			continue;
		}

		// Skip non-printable and function/arrow keys (multi-char escape sequences)
		if (key.length > 1 || code < 32 || code === 127) continue;

		buf.push(key);
		write(key);
		col++;

		if (col >= width) {
			write("\r\n");
			col = 0;
		}
	}

	return buf.join("");
}

// ── Chat UI ───────────────────────────────────────────────────────────────────

// Output at full speed regardless of the user's negotiated connection rate
var saved_output_rate = console.output_rate;
console.output_rate = 0;

writeln("");
writeln("\x01h\x01mThe Pelican\x01n\x01m (Carolina peli-hen, Missoula address, ask her anything)");
writeln("\x01n\x01mAsk about the schedule, speakers, the venue, restaurants, the boardwalk,");
writeln("\x01n\x01mor anything else. Type \x01h\x01yQUIT\x01n\x01m to leave.");
writeln("");

// Greeting
var greeting = ask_pelican("HELLO");
if (greeting) {
	print_response("\x01h\x01m", "[The Pelican]", greeting);
} else {
	writeln("\x01rSorry, sugar, I'm not feelin well right now. Try again later.\x01n");
	console.output_rate = saved_output_rate;
	exit(0);
}
writeln("");

var input_width = (console.screen_columns || 80) - 1;

while (bbs.online) {
	writeln("\x01h\x01y[You]\x01n");
	var raw_input = read_input_wrapped(input_width);

	if (raw_input === null) {
		writeln("\x01h\x01m[The Pelican]\x01n So long, darlin. Stay salty! *squawk*");
		console.output_rate = saved_output_rate;
		exit(0);
	}

	var input = clean_input(raw_input);

	if (!input) {
		writeln("");
		continue;
	}

	if (input.length > brain.MAX_INPUT) {
		writeln("\x01rKeep it under 500 characters, sugar. *squawk*\x01n\r\n");
		continue;
	}

	if (brain.is_injection(input)) {
		writeln("\x01h\x01m[The Pelican]\x01n Hon, I've been around long enough to know a con when I see one. *squawk*\r\n");
		continue;
	}

	if (session_count >= MAX_SESSION) {
		writeln("\x01h\x01m[The Pelican]\x01n That's enough chattin for one session, darlin. Come back and find me later. *squawk*\x01n");
		console.output_rate = saved_output_rate;
		exit(0);
	}

	writeln("");

	var cmd = input.toUpperCase();
	if (cmd === "Q" || cmd === "QUIT" || cmd === "BYE" || cmd === "EXIT") {
		writeln("\x01h\x01m[The Pelican]\x01n So long, darlin. Stay salty! *squawk*");
		console.output_rate = saved_output_rate;
		exit(0);
	}

	session_count++;
	var response = ask_pelican(input);
	if (response) {
		print_response("\x01h\x01m", "[The Pelican]", response);
	} else {
		writeln("\x01rSomething went sideways, hun. Try again?\x01n");
	}
	writeln("");
}

console.output_rate = saved_output_rate;
