// post_foodbark.js
// Posts staged foodbark.io essays into the Local:FOODBARK sub.
//
// Run with: /sbbs/exec/jsexec mods/exec/post_foodbark.js
// Cron runs scripts/foodbark_feed.py first; that fetches the RSS and writes
// data/foodbark_pending.json. This half exists only because Synchronet message
// bases can be written through the JS MsgBase object and nothing else, so the
// python side cannot post them itself.
//
// Idempotent: every posted guid is appended to data/foodbark_posted.txt, which
// the python side diffs against on the next run. Re-running with nothing staged
// is a no-op.
//
// ART: if text/foodbark/<slug>.ans exists, where <slug> is the last path
// segment of the article link, it is prepended to the message body. This is
// opt-in per article by design. Article images are a mixed bag: photographs
// and illustrations convert beautifully to half-block ANSI, but screenshots
// of text turn to mush at 70 columns and no encoder setting rescues them.
// Curating by dropping in a file beats auto-converting whatever appeared
// first in the HTML. Make them with scripts/img2ans.py --width 70.
//
// Flags:
//   --dry-run          assemble everything, report, write nothing
//   --pending=<path>   read staged items from somewhere else (testing)

"use strict";

var SUB_CODE  = "LOCAL-FOODBARK";
var FROM      = "foodbark";
var FROM_EXT  = "1";

var REPO      = "/home/ubuntu/naclcon-bbs/";
var PENDING   = "data/foodbark_pending.json";
var POSTED    = "data/foodbark_posted.txt";
var ART_DIR   = system.text_dir + "foodbark/";

var dry_run = false;
var pending_override = "";
for (var a = 0; a < argv.length; a++) {
	var opt = "" + argv[a];
	if (opt === "--dry-run") dry_run = true;
	var m = opt.match(/^--pending=(.+)$/);
	if (m) pending_override = m[1];
}

function read_file(path) {
	var f = new File(path);
	if (!f.open("r")) return null;
	var s = f.read();
	f.close();
	return s;
}

function append_line(path, line) {
	var f = new File(path);
	if (!f.open(file_exists(path) ? "a" : "w")) {
		log(LOG_WARNING, "post_foodbark: cannot write " + path);
		return false;
	}
	f.writeln(line);
	f.close();
	return true;
}

// https://foodbark.io/posts/stand-up-soba/ -> "stand-up-soba"
function slug_of(link) {
	if (!link) return "";
	var s = ("" + link).replace(/[?#].*$/, "").replace(/\/+$/, "");
	var i = s.lastIndexOf("/");
	return (i >= 0) ? s.substring(i + 1) : s;
}

// Read as binary: the art is CP437 (raw 0xDF) to match the rest of text/, and
// Synchronet translates it for UTF-8 terminals on its own inside a session.
function read_bin(path) {
	var f = new File(path);
	if (!f.open("rb")) {
		log(LOG_WARNING, "post_foodbark: cannot read art " + path);
		return null;
	}
	var s = f.read();
	f.close();
	return s || null;
}

// An article can carry several images: <slug>-1.ans, <slug>-2.ans, ...
// (<slug>.ans is still honoured for a single one.) Built by
// scripts/foodbark_art.py, which also writes the matching web PNG.
function art_files(slug) {
	if (!slug) return [];
	var found = directory(ART_DIR + slug + "-*.ans").sort();
	if (file_exists(ART_DIR + slug + ".ans"))
		found.unshift(ART_DIR + slug + ".ans");
	return found;
}

// Wrap each piece in plain-ASCII sentinels naming its web image.
//
// The web frontend cannot show this art: Synchronet's html_encode predates
// 24-bit colour and mis-parses it, and stock webv4 strips ANSI anyway, which
// would leave a screenful of naked half-block bytes above the essay. So the
// browser swaps the whole marked block for the matching PNG, which holds the
// identical pixels (webv4/root/js/foodbark-art.js).
//
// The markers are deliberately Ctrl-A coloured, not plain: Synchronet renders
// them dim grey in the terminal, while the web strips Ctrl-A before it strips
// ANSI, so "[art:name]" survives in the browser for the script to find.
function art_block(path) {
	var data = read_bin(path);
	if (!data) return null;
	var name = file_getname(path).replace(/\.ans$/i, "");
	return "\x01h\x01k[art:" + name + "]\x01n\r\n" +
	       data + "\r\n" +
	       "\x01h\x01k[/art]\x01n\r\n\r\n";
}

var raw = pending_override ? read_file(pending_override) : null;
if (raw === null && !pending_override)
	raw = read_file(system.data_dir + "foodbark_pending.json");
if (raw === null) raw = read_file(REPO + PENDING);
if (raw === null) {
	print("nothing staged (no foodbark_pending.json); run scripts/foodbark_feed.py first");
	exit(0);
}

var pending;
try {
	pending = JSON.parse(raw);
} catch (e) {
	print("ERROR: foodbark_pending.json is not valid JSON: " + e);
	exit(1);
}
if (!pending.length) {
	print("nothing to post (0 staged)");
	exit(0);
}

var mb = null;
if (!dry_run) {
mb = new MsgBase(SUB_CODE);
if (!mb.open()) {
	print("ERROR: cannot open msgbase " + SUB_CODE + " (" + mb.error + ")");
	print("If the sub is new, ctrl/msgs.ini must be deployed; jsexec reads it fresh,");
	print("but the running sbbs needs a restart before callers can see the sub.");
	exit(1);
}
}

var posted = 0, failed = 0, illustrated = 0;
for (var i = 0; i < pending.length; i++) {
	var e = pending[i];
	var body = e.body + "\r\n\r\n" + "-- " + "\r\n" + e.link + "\r\n";
	body = body.replace(/\r?\n/g, "\r\n");

	// Prepend the art AFTER the newline normalisation above, never before.
	// That regex would otherwise run over the escape sequences, and the art's
	// row endings are already exactly CRLF.
	var slug = slug_of(e.link);
	var files = art_files(slug);
	var art = "";
	for (var a = 0; a < files.length; a++) {
		var block = art_block(files[a]);
		if (block) art += block;
	}
	if (art) {
		body = art + body;
		illustrated++;
	}
	if (dry_run) {
		print("  " + (art ? "[art] " : "[   ] ") + e.title.substr(0, 52));
		print("        slug=" + slug + "  body=" + body.length + " bytes" +
		      (art ? "  art=" + art.length + " in " + files.length + " image(s)"
		           : "  (no " + ART_DIR + slug + "*.ans)"));
		posted++;
		continue;
	}

	var hdr = {
		to:       "All",
		from:     FROM,
		from_ext: FROM_EXT,
		subject:  e.title.substr(0, 70)
	};
	// Preserve the original publication date so the sub reads chronologically
	// rather than showing 38 essays all stamped with today's backfill run.
	var when = Date.parse(e.date);
	if (!isNaN(when)) hdr.when_written_time = Math.floor(when / 1000);

	if (mb.save_msg(hdr, body)) {
		posted++;
		append_line(REPO + POSTED, e.guid);
		append_line(system.data_dir + "foodbark_posted.txt", e.guid);
	} else {
		failed++;
		log(LOG_WARNING, "post_foodbark: save_msg failed for " + e.guid);
		print("  FAILED: " + e.title);
	}
}
if (mb) mb.close();

print((dry_run ? "would post " : "posted ") + posted + " of " + pending.length +
      " to " + SUB_CODE + (failed ? " (" + failed + " failed)" : "") +
      ", " + illustrated + " with art");

// Clear the staging file so a re-run before the next fetch is a no-op.
if (posted && !failed && !dry_run) {
	for (var p = 0; p < 2; p++) {
		var path = (p === 0) ? (REPO + PENDING) : (system.data_dir + "foodbark_pending.json");
		var f = new File(path);
		if (f.open("w")) { f.write("[]\n"); f.close(); }
	}
}

if (posted) {
	print("QWK/network note: this is a Local sub, so nothing leaves the board.");
}
