// post_arcade_and_bbses.js
// Run once with: /sbbs/exec/jsexec mods/exec/post_arcade_and_bbses.js
// Posts two announcements to LOCAL-NOTICES:
//   1. NaClCON Arcade (door games)
//   2. BBSes We Like (curated connect menu)

var FROM     = "foodbark";
var FROM_EXT = "1";            // sysop user number
var NOTICES  = "LOCAL-NOTICES";

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

// ---------------------------------------------------------------------
// 1. NaClCON Arcade
// ---------------------------------------------------------------------

var arcade_lines = [
	"Fifteen classic BBS door games are now live on NaClCON.",
	"",
	"From the main menu, pick 'Games & Apps' (hotkey A) and go into",
	"'NaClCON Arcade'. Hotkey in, play, back out. Scores and characters",
	"persist on A-Net Online (game.a-net-online.lol) -- they're shared",
	"with anyone else playing these games across BBSes that pass through",
	"to A-Net, so you're entering a live multi-BBS leaderboard, not a",
	"sandbox of one.",
	"",
	"The lineup:",
	"",
	"  LORD 4.08             Legend of the Red Dragon. The BBS RPG.",
	"                        Slay dragons, flirt with Violet, win Seth",
	"                        Able's original kingdom.",
	"  NukeWars 3.8          Cold War strategy. Escalate and annihilate.",
	"  Buccaneer             Pirate trader/combat. Fantasy Caribbean.",
	"  Darkness              Darker-toned fantasy RPG.",
	"  Netrunner             Cyberpunk corporate espionage. Fits the",
	"                        hacker-con vibe.",
	"  High Seas             Age-of-sail naval combat and treasure.",
	"  Synchronetris         Tetris on the BBS. Networked high scores.",
	"  OOKII (Omega)         Operation Overkill II, Omega world.",
	"  OOKII (Deathland)     OOKII, Deathland world.",
	"  Trade Wars 2002       The classic space-trading door.",
	"                        InterBBS universe.",
	"  Drug Lord             Street-economy sim.",
	"  Video Poker           What it says on the tin.",
	"  The Clans (777)       Multi-player fantasy RPG by Allen Ussher,",
	"                        modernized by Deuce. InterBBS on fsxNet",
	"                        777 X-League -- your char shares the world",
	"                        with every Clans player in the league.",
	"  NetHack               The classic roguelike, via A-Net.",
	"",
	"Plus Synchronet Minesweeper (local, graphical, mouse-aware) if you",
	"want a palate cleanser between dragon slayings.",
	"",
	"Credit: most of these doors are hosted by A-Net Online",
	"(https://a-net-online.lol/gameserver, sysop StingRay). They run",
	"a door hub with 450+ games; we rlogin into their server with the",
	"BBS tag -s-nacl. No local installs. Big thanks to StingRay for",
	"keeping that hub alive.",
	"",
	"Dial in, ladder up, talk trash in the message boards.",
	"",
	"- foodbark"
];

// ---------------------------------------------------------------------
// 2. BBSes We Like
// ---------------------------------------------------------------------

var bbses_lines = [
	"New on the main menu: 'BBSes We Like' -- a curated connect menu to",
	"six handpicked boards, reachable directly from inside NaClCON via",
	"Synchronet's telnet gateway. Pick a number, we bridge you in.",
	"Hit Ctrl-] during a remote session for the gateway control menu",
	"(q to disconnect cleanly).",
	"",
	"  20 for Beers",
	"    telnet 20forbeers.com",
	"    Chill sysop-run board for beer nerds and regulars.",
	"",
	"  ACiD Underworld",
	"    telnet blackflag.acid.org",
	"    ACiD Productions -- the ANSI art collective that practically",
	"    invented the visual language of 90s underground BBSes.",
	"",
	"  Bottomless Abyss",
	"    ssh bbs.bottomlessabyss.net -p 2222",
	"    Long-running Synchronet BBS. SSH-only, so you'll need to",
	"    connect from your own terminal -- we can't bridge SSH out",
	"    from inside the BBS.",
	"",
	"  Al's Geek Lab",
	"    telnet bbs.alsgeeklab.com -p 2323",
	"    Al of YouTube fame. Retro computing and BBS hobbyist hub.",
	"    Good introduction for newcomers.",
	"",
	"  Telehack",
	"    telnet telehack.com",
	"    Simulated 80s ARPANET. Play with VAXen, mail old ghosts,",
	"    find usenet relics. An endless toy.",
	"",
	"  Particles! BBS",
	"    telnet particlesbbs.dyndns.org -p 6400",
	"    Modern Mystic BBS. Active doors, active sysop.",
	"",
	"Etiquette -- these are other sysops' houses:",
	"",
	"  * Register as yourself. No spam signups.",
	"  * Read the rules. Every board has them.",
	"  * Say hi to the sysop when you make an account.",
	"  * Post. A BBS with no posts is a ghost town.",
	"",
	"If you know good boards that should be on the list, drop me a",
	"message -- we can add them.",
	"",
	"- foodbark"
];

// ---------------------------------------------------------------------

print("Posting to " + NOTICES + "...");
post(NOTICES, "New door games: NaClCON Arcade (15 classics live)", arcade_lines.join("\r\n"));
post(NOTICES, "New feature: BBSes We Like (curated connect menu)",   bbses_lines.join("\r\n"));
print("Done.");
