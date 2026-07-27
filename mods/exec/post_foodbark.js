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

"use strict";

var SUB_CODE  = "LOCAL-FOODBARK";
var FROM      = "foodbark";
var FROM_EXT  = "1";

var REPO      = "/home/ubuntu/naclcon-bbs/";
var PENDING   = "data/foodbark_pending.json";
var POSTED    = "data/foodbark_posted.txt";

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

var raw = read_file(system.data_dir + "foodbark_pending.json");
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

var mb = new MsgBase(SUB_CODE);
if (!mb.open()) {
	print("ERROR: cannot open msgbase " + SUB_CODE + " (" + mb.error + ")");
	print("If the sub is new, ctrl/msgs.ini must be deployed; jsexec reads it fresh,");
	print("but the running sbbs needs a restart before callers can see the sub.");
	exit(1);
}

var posted = 0, failed = 0;
for (var i = 0; i < pending.length; i++) {
	var e = pending[i];
	var body = e.body + "\r\n\r\n" + "-- " + "\r\n" + e.link + "\r\n";
	body = body.replace(/\r?\n/g, "\r\n");

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
mb.close();

print("posted " + posted + " of " + pending.length + " to " + SUB_CODE +
      (failed ? " (" + failed + " failed)" : ""));

// Clear the staging file so a re-run before the next fetch is a no-op.
if (posted && !failed) {
	for (var p = 0; p < 2; p++) {
		var path = (p === 0) ? (REPO + PENDING) : (system.data_dir + "foodbark_pending.json");
		var f = new File(path);
		if (f.open("w")) { f.write("[]\n"); f.close(); }
	}
}

if (posted) {
	print("QWK/network note: this is a Local sub, so nothing leaves the board.");
}
