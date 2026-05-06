// New User Registration Prompts module — NaClCON override
// Customizations vs stock /sbbs/exec/newuser_prompts.js:
//   - get_name (real name) accepts blank
//   - get_netmail (email) accepts blank; forwarding only asked if email entered

require("sbbsdefs.js", "UQ_ALIASES");
require("key_defs.js", "K_EDIT");
require("userdefs.js", "U_NAME");
require("gettext.js", "gettext");

var prompts = bbs.mods.prompts || load(bbs.mods.prompts = {}, "user_info_prompts.js", "new user registration");

var options = load("modopts.js", "newuser_prompts", {});

"use strict";

function get_name_optional() {
	if (!((system.newuser_questions & UQ_ALIASES) && (system.newuser_questions & UQ_REALNAME)))
		return;
	var kmode = (system.newuser_questions & UQ_NOEXASC) | K_EDIT | K_AUTODEL | K_TRIM;
	if (!(system.newuser_questions & UQ_NOUPRLWR))
		kmode |= K_UPRLWR;
	while (bbs.online && bbs.text(bbs.text.EnterYourRealName)) {
		console.putmsg(bbs.text(bbs.text.EnterYourRealName), P_SAVEATR);
		var name = console.getstr(user.name, LEN_NAME, kmode);
		if (console.aborted) {
			prompts.ask_to_cancel();
			continue;
		}
		if (!name) break;  // blank accepted
		if (!system.check_name(name, /* unique: */true)
			|| !system.check_realname(name)
			|| ((system.newuser_questions & UQ_DUPREAL)
				&& bbs.matchuserdata(U_NAME, name))) {
			bbs.logline(LOG_NOTICE, "N!", format("Invalid or duplicate user real name: '%s'", name));
			prompts.ask_to_cancel(bbs.text(bbs.text.YouCantUseThatName));
		} else {
			user.name = name;
			break;
		}
	}
}

function get_netmail_optional() {
	while (bbs.online && bbs.text(bbs.text.EnterNetMailAddress)) {
		console.putmsg(bbs.text(bbs.text.EnterNetMailAddress));
		var netmail = console.getstr(user.netmail, LEN_NETMAIL,
			K_EDIT | K_AUTODEL | K_LINE | K_TRIM);
		if (console.aborted) {
			prompts.ask_to_cancel();
			continue;
		}
		if (!netmail) break;  // blank accepted
		if (bbs.trashcan(netmail, "email")
			|| ((system.newuser_questions & UQ_DUPNETMAIL)
				&& bbs.matchuserdata(U_NETMAIL, netmail))) {
			prompts.ask_to_cancel(bbs.text(bbs.text.YouCantUseThatNetmail));
		} else {
			user.netmail = netmail;
			break;
		}
	}
}

while(bbs.online && !js.terminated) {

	if (options.lang)
		prompts.get_lang();
	prompts.get_terminal(user, options);
	prompts.get_alias();
	get_name_optional();
	if (!bbs.online)
		exit(1);
	if (!user.alias) {
		log(LOG_ERR, "New user alias was blank");
		exit(1);
	}
	if (!user.handle)
		user.handle = user.alias;
	user.handle = user.handle.trimRight();
	if (system.newuser_questions & UQ_HANDLE)
		prompts.get_handle();
	if (system.newuser_questions & UQ_ADDRESS)
		prompts.get_address();
	if (system.newuser_questions & (UQ_ADDRESS | UQ_LOCATION))
		prompts.get_location();
	if (system.newuser_questions & UQ_ADDRESS)
		prompts.get_zipcode();
	if (system.newuser_questions & UQ_PHONE)
		prompts.get_phone();
	if (system.newuser_questions & UQ_SEX)
		prompts.get_gender();
	if (system.newuser_questions & UQ_BIRTH)
		prompts.get_birthdate();
	if (!(system.newuser_questions & UQ_NONETMAIL)) {
		get_netmail_optional();
		if (user.netmail)
			prompts.get_netmail_forwarding();
	}

	if (!bbs.text(bbs.text.UserInfoCorrectQ) || console.yesno(bbs.text(bbs.text.UserInfoCorrectQ)))
		break;
	prompts.ask_to_cancel();
	console.print(gettext("Restarting new user registration") + "\r\n");
}
