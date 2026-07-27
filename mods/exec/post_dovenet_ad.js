// post_dovenet_ad.js
// One-shot: posts text/dovenet_ad.msg to the DOVE-Net Advertisements sub.
// Run with: /sbbs/exec/jsexec mods/exec/post_dovenet_ad.js
// Converts ^A (caret + A, two ASCII chars) to \x01 Ctrl-A before posting.

var FROM      = "foodbark";
var FROM_EXT  = "1";
var SUB_CODE  = (typeof argv !== "undefined" && argv.length > 0) ? argv[0] : "DOVE-ADS";
var SUBJECT   = "foodbark BBS: personal board in Missoula, NaClCON 2026 archive aboard";
var BODY_FILE = system.text_dir + "dovenet_ad.msg";

var f = new File(BODY_FILE);
if (!f.open("r")) {
	print("ERROR: cannot open " + BODY_FILE);
	exit(1);
}
var raw = f.read();
f.close();

var body = raw.replace(/\^A/g, "\x01").replace(/\r?\n/g, "\r\n");

var mb = new MsgBase(SUB_CODE);
if (!mb.open()) {
	print("ERROR: cannot open msgbase " + SUB_CODE);
	exit(1);
}
var hdr = {
	to:       "All",
	from:     FROM,
	from_ext: FROM_EXT,
	subject:  SUBJECT
};
var ok = mb.save_msg(hdr, body);
mb.close();

if (ok) {
	print("posted to " + SUB_CODE + ": " + SUBJECT);
	print("triggering QWK callout: touch /sbbs/data/qnet/vert.now");
	print("(daemon honors at next event tick; full propagation at 00/06/12/18 UTC)");
} else {
	print("FAILED to post to " + SUB_CODE);
	exit(1);
}
