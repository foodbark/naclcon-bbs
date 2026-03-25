// post_speakers.js
// Run once with: jsexec mods/exec/post_speakers.js
// Posts speaker list to LOCAL-NOTICES and individual speaker threads to LOCAL-TALKS.

var FROM      = "foodbark";
var FROM_EXT  = "1";           // sysop user number
var NOTICES   = "LOCAL-NOTICES";
var TALKS     = "LOCAL-TALKS";

// -----------------------------------------------------------------------
// Speaker data
// -----------------------------------------------------------------------
var speakers = [
	{
		name:  "Lee Felsenstein",
		talk:  "Homebrew Computing Club, Me and My Big Ideas, The History of Hacking",
		bio:   "Computer engineer central to personal computer development. Original Homebrew Computer Club member. Designed the Osborne 1 (first mass-produced portable computer), the Sol-20, the PennyWhistle modem, and the VDM-1 video display module."
	},
	{
		name:  "Chris Wysopal (Weld Pond)",
		talk:  "The Accidental Cyber Think Tank: How the L0pht Forced the World to Take Software Security Seriously",
		bio:   "Early L0pht Heavy Industries member who helped turn vulnerability research public. Part of the crew that testified before the U.S. Senate in 1998, warning they could take down the Internet in 30 minutes. Co-founded Veracode."
	},
	{
		name:  "G. Mark Hardy",
		talk:  "A Hacker Looks at 50",
		bio:   "President of National Security Corporation and co-host of the CISO Tradecraft podcast. Over 40 years of cybersecurity expertise to government, military, and commercial clients. Author of 100+ articles. Holds a BS in Computer Science, BA in Mathematics, MBA, Masters in Strategic Studies, CISSP, and CISM."
	},
	{
		name:  "Richard Thieme",
		talk:  "I began addressing the human impacts of technological change -- specifically the arrival of the public internet -- 32 years ago",
		bio:   "Author and professional speaker on technology challenges and the future. Published eight books including the Mobius Trilogy. Spoke at DEF CON 27 times. Has keynoted conferences in 15 countries."
	},
	{
		name:  "Johnny Shaieb",
		talk:  "Axiomatic Events that Evolved Vulnerability Databases",
		bio:   "PhD candidate at the University of Tulsa (dissertation on vulnerability database history and scoring). Global Delivery Leader and Chief Architect of IBM's Cyber Threat Exposure Management. Over 25 years of offensive security experience. Created the \"Hac-King-Do\" framework and co-founded X-Force Red's hacker internship program."
	},
	{
		name:  "Andrew Brandt",
		talk:  "Bring Me (Back) To Life: Running Early Hacking Tools on Obsolete Computers",
		bio:   "Over 20 years in cybersecurity. Former director of threat research at Symantec and Blue Coat Systems; principal researcher at Sophos and Netcraft; investigative journalist and editor at PC World. Original member of San Francisco's Otaku Patrol Group. Volunteers as docent for the Media Archaeology Lab."
	},
	{
		name:  "Heidi and Bruce Potter",
		talk:  "AMA with the Potters",
		bio:   "Bio to follow."
	},
	{
		name:  "Brian Harden (noid)",
		talk:  "Community Organizing Before Social Media... How We Did It",
		bio:   "Organized LA 2600 meetings in the 90s. Built DC206 in the early 2000s. Helped create DEF CON. Largely retired from the scene. Works on a farm. Writes about himself in third person."
	},
	{
		name:  "Izaac Falken",
		talk:  "The Persistent Antipattern'); DROP TABLE keynote; -- In-band Signaling",
		bio:   "Hacker of the 1990s and beyond. Associated with 2600 Magazine and Off The Hook radio program. Thirty years in professional computer security consulting."
	},
	{
		name:  "Mei Danowski",
		talk:  "Subduing the Enemy Without Fighting: Ancient Strategy and the Birth of China's Early Hacker Imagination",
		bio:   "Founder and principal of Natto Thoughts advisory firm. Expertise in geopolitical, economic, social, cultural, and linguistic cyber threat analysis. Previous roles at Microsoft, Accenture, and Verisign. U.S. government support experience."
	},
	{
		name:  "B.K. DeLong (McIntyre)",
		talk:  "In January 1999, a small group of volunteers at Attrition.org decided to do something no one else was doing systematically: capture and archive defaced websites",
		bio:   "Staff contributor at Attrition.org in the late 1990s and early 2000s. Responsible for capturing, verifying, and archiving web defacements. Catalogued over 15,000 defaced sites. Currently Product Owner and Lead Engineer in Enterprise Vulnerability Management."
	},
	{
		name:  "Edison Carter",
		talk:  "Digital Hooligan: Origin and Exploits of an Old-School Hacker and Phone Phreak",
		bio:   "Old-school hacker and phone phreak from the 80s and 90s, active from the mid-80s to the mid-90s."
	},
	{
		name:  "Jericho",
		talk:  "Life in an Early 90's Hacker Group",
		bio:   "Over 33 years in the hacker and security scene. Hacker-turned-security professional with no degree or certifications. Advocate for advancing the field and champion of security industry integrity."
	},
	{
		name:  "Josh Corman",
		talk:  "TBA",
		bio:   "Thirty years in hacker culture. Philosopher background. Shifted focus to public policy and the public good. Launched \"I am the Cavalry\" in 2013 to address over-dependence on undependable technology. Has held AppSec, CTO, and CSO roles. Designed and implemented the CISA COVID Task Force. Currently driving UnDisruptable27 for Taiwan Conflict disruption preparedness."
	},
	{
		name:  "Casey John Ellis",
		talk:  "Smashing the (Policy) Stack for... Public Safety & (Not) Profit?!",
		bio:   "Serial entrepreneur and founder of Bugcrowd, co-founder of the disclose.io Project. Over 25 years in information security. Launched the first bug bounty programs on Bugcrowd in 2012. Has advised the US White House, DoD, DOJ, DHS/CISA, and Australian and UK intelligence on election cybersecurity, National Cyber Strategy, security research policy, and AI policies. Native of Sydney, Australia; based in the San Francisco Bay Area."
	},
	{
		name:  "Jamie Arlen",
		talk:  "FAIL: An Epic Career of Doing All the Wrong Things and Somehow Still Being Right",
		bio:   "Over 30 years of security and engineering experience. Former Contributing Analyst at Securosis. Blogger and podcaster with Liquidmatrix Security Digest. Frequent conference speaker. Lead author for Cloud Security Alliance Security Guidance V4."
	}
];

var fireside = [
	{
		name:  "Hack Beer'd",
		talk:  "Avast, ye LAN lubbers! Grab a grog and park yer ParrotOS while cap'n HackBeer'd tells a `tail -f /dev/urandom`.",
		bio:   "The most infamous hacker buccaneer on the seven networks. Sailed with a crew including Bobby TABLES. Accompanied by a parrot named Pollymorphic."
	},
	{
		name:  "Dustin Heywood (EvilMog)",
		talk:  "The Early Hashcat Beta Days, the Rise of the Alberta Hashcat Super Cluster, DROWN, and More",
		bio:   "Senior Technical Leader at IBM X-Force. Semi-retired Team Hashcat member. Bishop of the Church of Wifi. Multi-time Hacker Jeopardy World Champion. Black Badge collector."
	}
];

// -----------------------------------------------------------------------
// Helper: post one message
// -----------------------------------------------------------------------
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

// -----------------------------------------------------------------------
// 1. NOTICES: full speaker list (names + talk titles)
// -----------------------------------------------------------------------
print("Posting speaker list to " + NOTICES + "...");

var lines = [];
lines.push("NaClCON 2026 -- May 31 - June 2, Carolina Beach, NC");
lines.push("Full speaker list: naclcon.com/speakers");
lines.push("");
lines.push("MAIN STAGE");
lines.push("----------");
for (var i = 0; i < speakers.length; i++) {
	lines.push(speakers[i].name);
	lines.push("  " + speakers[i].talk);
	lines.push("");
}
lines.push("FIRESIDE CHATS");
lines.push("--------------");
for (var i = 0; i < fireside.length; i++) {
	lines.push(fireside[i].name);
	lines.push("  " + fireside[i].talk);
	lines.push("");
}

post(NOTICES, "NaClCON 2026 Speaker List", lines.join("\r\n"));

// -----------------------------------------------------------------------
// 2. TALKS: one thread per speaker
// -----------------------------------------------------------------------
print("\nPosting individual speaker threads to " + TALKS + "...");

var all = speakers.concat(fireside);
for (var i = 0; i < all.length; i++) {
	var s = all[i];
	var body = [];
	body.push(s.name);
	body.push("");
	body.push("Talk: " + s.talk);
	body.push("");
	body.push(s.bio);
	body.push("");
	body.push("-- naclcon.com/speakers");
	post(TALKS, s.name + " -- " + s.talk.substring(0, 40) + (s.talk.length > 40 ? "..." : ""), body.join("\r\n"));
}

print("\nDone.");
