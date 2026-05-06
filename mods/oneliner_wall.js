// Hooked from mods/logon.js between the random splash and EVENT_LOGON.
// Runs the stock oneliners wall (xtrn ONELINER) and returns. The wall is
// the only slice of the logon sandwich after the splash.

bbs.exec_xtrn("ONELINER");
