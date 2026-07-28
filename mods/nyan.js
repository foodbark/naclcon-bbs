// nyan.js - Plays the half-block ANSI animation in text/nyan/ as a loop.
//
// The frames were produced from an animated source by scripts/img2ans.py at
// 80 columns by 16 character rows. Each is a full redraw: roughly 90% of the
// cells change between frames (the trail scrolls across the whole width), so
// there is nothing worth delta-encoding and each frame is about 28KB.
//
// Each row carries an absolute cursor move (ESC[row;1H), so the art does not
// depend on the terminal being exactly 80 columns wide. Relying on auto-wrap
// instead, the way art/logo.ans does, shears the picture diagonally on any
// wider window.
//
// Run from a menu or xtrn as *nyan, or directly:
//   /sbbs/exec/jsexec mods/nyan.js 3          <- three loops then stop
//   /sbbs/exec/jsexec mods/nyan.js 3 ascii    <- spaces only, no half block
//
// Arguments (order does not matter after the loop count):
//   [0]     number of loops. 0 or absent means run until a key is pressed.
//   "utf8"  force UTF-8 output   (already the default outside a BBS session)
//   "cp437" force raw 0xDF bytes (already the default inside one)
//   "ascii" use the space-cell frame set in text/nyan/ascii/
//
// The frames are stored CP437 (raw 0xDF) to match the rest of the art. Inside
// a BBS session Synchronet translates that for UTF-8 terminals itself, so the
// bytes go out untouched. Under jsexec there is no session and no translation,
// so UTF-8 is emitted by default; a raw 0xDF would otherwise land in a modern
// terminal as a replacement character.

"use strict";

require("sbbsdefs.js", "K_NONE");

var FRAME_MS  = 70;     // matches the source animation's frame durations
var loops     = (argv.length > 0) ? parseInt(argv[0], 10) : 0;

// A BBS session has `console`; jsexec does not. Synchronet translates CP437
// for UTF-8 terminals inside a session, but jsexec writes bytes straight
// through, so a raw 0xDF lands in a modern terminal as a replacement
// character. Default to UTF-8 whenever there is no session rather than
// making the caller remember a flag; pass cp437 to force the raw bytes.
var has_console = (typeof console === "object" && console !== null);

var want_utf8  = !has_console;
var want_ascii = false;
for (var a = 0; a < argv.length; a++) {
	var opt = String(argv[a]).toLowerCase();
	if (opt === "utf8")  want_utf8  = true;
	if (opt === "cp437") want_utf8  = false;
	if (opt === "ascii") want_ascii = true;
}

// ascii/ holds the same animation drawn with background-coloured spaces
// instead of half blocks: one cell per pixel, so half the vertical detail,
// but nothing outside plain ASCII. Use it when a terminal or font cannot
// draw U+2580 and paints replacement diamonds instead.
var FRAME_DIR = system.text_dir + (want_ascii ? "nyan/ascii/" : "nyan/");
if (want_ascii) want_utf8 = false;   // nothing to translate

// ── Load every frame up front ────────────────────────────────────────────────
// Reading from disk mid-animation would stutter, and the whole set is small
// enough to hold in memory.

var frames = [];
var listing = directory(FRAME_DIR + "frame*.ans").sort();
for (var i = 0; i < listing.length; i++) {
	var f = new File(listing[i]);
	if (!f.open("rb")) continue;
	var data = f.read();
	f.close();
	// Emit the raw UTF-8 bytes for U+2580 rather than the character itself,
	// so the encoding does not depend on how write() treats a wide char.
	if (want_utf8) data = data.replace(/\xdf/g, "\xe2\x96\x80");
	frames.push(split_rows(data));
}

// Split a frame at its row boundaries (each row begins with ESC[<n>;1H).
//
// Frames are written a row at a time rather than as one ~32KB blob. A single
// large write gets chunked somewhere below us, and if a chunk boundary lands
// in the middle of the 3-byte UTF-8 half block, the terminal sees a truncated
// sequence, waits, gives up across the frame delay and paints U+FFFD. Rows
// always end just after a complete glyph, so splitting there cannot tear a
// character. Done with indexOf rather than a lookahead split, which older
// SpiderMonkey handles inconsistently.
function split_rows(s) {
	var rows = [];
	var start = s.indexOf("\x1b[");
	if (start !== 0) start = 0;
	var i = start;
	while (i < s.length) {
		var next = s.indexOf("\x1b[", i + 1);
		// Only break at a row move (ESC[<digits>;1H), not at a colour SGR.
		while (next > -1 && !/^\x1b\[\d+;1H/.test(s.substr(next, 12)))
			next = s.indexOf("\x1b[", next + 1);
		if (next === -1) { rows.push(s.substring(i)); break; }
		rows.push(s.substring(i, next));
		i = next;
	}
	return rows;
}

if (!frames.length) {
	writeln("\r\nNo frames found in " + FRAME_DIR);
	exit(1);
}

// ── Play ─────────────────────────────────────────────────────────────────────

// jsexec has no terminal session, so `console` is undefined there. Fall back
// to plain write() so the module can be exercised headlessly:
//   jsexec mods/nyan.js 2 > out.bin
var out = has_console ? function (s) { console.write(s); }
                      : function (s) { write(s); };

var saved_rate = 0;
if (has_console) {
	saved_rate = console.output_rate;
	console.output_rate = 0;      // ignore the negotiated baud emulation
	console.clear();
}
out("\x1b[?25l");                 // hide cursor

var count = 0;
var stop = false;

while (!stop) {
	for (var n = 0; n < frames.length; n++) {
		// Each row carries its own absolute position, so no cursor-home is
		// needed and the frame overpaints the previous one exactly.
		var rows = frames[n];
		for (var r = 0; r < rows.length; r++) out(rows[r]);
		mswait(FRAME_MS);

		// Any keypress bails out. K_NONE returns immediately when nothing is
		// waiting, so this does not block the animation.
		if (has_console && console.inkey(K_NONE, 0)) {
			stop = true;
			break;
		}
	}
	count++;
	if (loops > 0 && count >= loops) stop = true;
}

out("\x1b[0m\x1b[?25h");          // reset attributes, show cursor
if (has_console) {
	console.gotoxy(1, 18);
	console.output_rate = saved_rate;
}
