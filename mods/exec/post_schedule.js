// post_schedule.js
// Run once with: jsexec mods/exec/post_schedule.js
// Posts the day-by-day NaClCON schedule to LOCAL-NOTICES.

var FROM      = "foodbark";
var FROM_EXT  = "1";
var NOTICES   = "LOCAL-NOTICES";

var lines = [];
lines.push("NaClCON 2026 Schedule -- now live at naclcon.com/schedule");
lines.push("May 31 - June 2, 2026  |  Carolina Beach, NC");
lines.push("Courtyard by Marriott Oceanfront");
lines.push("");
lines.push("Inside the BBS: View > NaClCON Schedule (lightbar shell)");
lines.push("");
lines.push("(Schedule subject to change. Times are local.)");
lines.push("");
lines.push("SUNDAY, MAY 31  --  Day 1");
lines.push("-------------------------");
lines.push("  1:00p - 2:00p  Registration & Bag Check");
lines.push("  2:00p - 4:00p  Opening Ceremony with CTF & Badge Intro");
lines.push("                 (Dead Meat Society, Shipstone)");
lines.push("  4:00p - 6:00p  Hotel Check-In & Welcome Mixer / Open Bar (BSides312)");
lines.push("  6:00p - 8:00p  Speaker Dinner @ Sunny Daze BBQ");
lines.push("  6:00p - 7:00p  Boardwalk Bar Crawl");
lines.push("  7:00p -11:00p  Hotel Pool Party / Open Bar with DJ Lex Longa (BSides312)");
lines.push("  8:00p -11:00p  Saltcon Turtle Talks: Edison Carter, Dustin Heywood,");
lines.push("                 Tom Jackiewicz");
lines.push(" 11:00p - 2:00a  Boardwalk Bar Crawl");
lines.push("");
lines.push("MONDAY, JUNE 1  --  Day 2");
lines.push("-------------------------");
lines.push("  7:30a - 9:00a  Sweet Sunshine Breakfast");
lines.push("  9:00a - 5:00p  Vendor Village (open daily)");
lines.push("  9:00a -10:00a  Opening Keynote: Lee Felsenstein  (ThreatLocker)");
lines.push("                 Homebrew Computing Club, Me & My Big Ideas,");
lines.push("                 The History of Hacking");
lines.push(" 10:00a -11:00a  Edison Carter / Jericho");
lines.push("                 Life in an Early 90's Hacker Group");
lines.push(" 11:00a -12:00p  Josh Corman / Casey John Ellis");
lines.push("                 Smashing the (Policy) Stack for Public Safety");
lines.push("                 & (Not) Profit?!");
lines.push(" 12:00p - 1:00p  Heidi & Bruce Potter -- AMA with the Potters");
lines.push("  1:00p - 2:00p  Savory South BBQ Lunch  (Mitnick Security)");
lines.push("  2:00p - 3:00p  Andrew Brandt");
lines.push("                 Bring Me (Back) To Life: Running Early Hacking Tools");
lines.push("                 on Obsolete Computers");
lines.push("  3:00p - 4:00p  Johnny Shaieb");
lines.push("                 Axiomatic Events that Evolved Vulnerability Databases");
lines.push("  4:00p - 5:00p  Richard Thieme (remote)");
lines.push("                 Human Impacts of Technological Change");
lines.push("  5:00p - 6:00p  Happy Hour  (BSides312)");
lines.push("  6:00p - 8:00p  Hacker Jeopardy");
lines.push("  8:00p -11:00p  Saltcon Turtle Talks: Jeff Man, Noid, Cap'n Hack Beer'd");
lines.push(" 10:00p -11:00p  Dual Core -- Private Hotel Performance");
lines.push(" 11:00p - 2:00a  Boardwalk Bar Crawl");
lines.push("");
lines.push("TUESDAY, JUNE 2  --  Day 3");
lines.push("--------------------------");
lines.push("  7:30a - 9:00a  Shore to Fill Breakfast");
lines.push("  9:00a - 5:00p  Vendor Village (open daily)");
lines.push("  9:00a -10:00a  G. Mark Hardy -- A Hacker Looks at 50");
lines.push(" 10:00a -11:00a  B.K. DeLong (McIntyre)");
lines.push("                 Attrition.org and the Archive of 15,000 Defaced Sites");
lines.push(" 11:00a -12:00p  Jamie Arlen");
lines.push("                 FAIL: An Epic Career of Doing All the Wrong Things");
lines.push("                 and Somehow Still Being Right");
lines.push(" 12:00p - 1:00p  Brian Harden (Noid)");
lines.push("                 Community Organizing Before Social Media...");
lines.push("                 How We Did It");
lines.push("  1:00p - 2:00p  Taco Tuesday Beach Lunch  (Mitnick Security)");
lines.push("  2:00p - 3:00p  Izaac Falken");
lines.push("                 The Persistent Antipattern'); DROP TABLE keynote; --");
lines.push("                 In-band Signaling");
lines.push("  3:00p - 4:00p  Mei Danowski");
lines.push("                 Subduing the Enemy Without Fighting: Ancient Strategy");
lines.push("                 and the Birth of China's Early Hacker Imagination");
lines.push("  4:00p - 5:00p  Closing Keynote: Chris Wysopal  (RedHelm)");
lines.push("  5:00p - 6:00p  Happy Hour with Book Signing  (BSides312)");
lines.push("  6:00p - 8:00p  Hacker Jeopardy");
lines.push("  8:00p -11:00p  Dinner & Closing Ceremony @ The Lazy Pirate");
lines.push(" 11:00p - 2:00a  Boardwalk Bar Crawl");
lines.push("");
lines.push("Speaker bios: see LOCAL-TALKS sub or 'NaClCON 2026 Speaker List' notice.");
lines.push("Pelican knows the schedule too -- ask her in chat.");
lines.push("");
lines.push("-- naclcon.com/schedule");

function post(sub_code, subject, body) {
	var mb = new MsgBase(sub_code);
	if (!mb.open()) {
		print("ERROR: could not open " + sub_code);
		return false;
	}
	var hdr = {
		to:       "All",
		from:     FROM,
		from_ext: FROM_EXT,
		subject:  subject
	};
	var ok = mb.save_msg(hdr, body);
	mb.close();
	if (ok)
		print("  posted: [" + sub_code + "] " + subject);
	else
		print("  FAILED: [" + sub_code + "] " + subject);
	return ok;
}

print("Posting NaClCON schedule to " + NOTICES + "...");
post(NOTICES, "NaClCON 2026 Schedule -- now live", lines.join("\r\n"));
print("Done.");
