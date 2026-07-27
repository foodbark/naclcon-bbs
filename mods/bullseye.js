// bullseye.js

// Bulletins written in Baja by Rob Swindell
// Translated to JS by Stehen Hurd
// Refactored by Rob Swindell

// @format.tab-size 4, @format.use-tabs true

require("sbbsdefs.js", "P_NOERROR");
require("gettext.js", 'gettext');

"use strict";

// Load the configuration file

var i=0;
var b=0;

writeln("");

console.line_counter=0;
var file=new File(system.text_dir+"bullseye.cfg");
if(!file.open("r", true)) {
	writeln("");
	writeln("!ERROR "+file.error+" opening "+ file.name);
	exit(1);
}
var p_mode = file.readln();
if (p_mode)
	p_mode = eval(p_mode);
bull = file.readAll();
file.close();

bull = bull.filter(function(str) { return truncsp(str) });

// Parse the config into display items. A line starting with '#' is a
// non-selectable section header; anything else is a bulletin, optionally
// followed by '|' and an explicit menu label (otherwise the label is derived
// from the filename, as it always was). Only bulletins consume a number.
var items = [];
var files = [];
for(i = 0; i < bull.length; ++i) {
	var line = truncsp(bull[i]);
	if(line.charAt(0) == '#') {
		items.push({ header: true, text: truncsp(line.slice(1).replace(/^\s+/, "")) });
		continue;
	}
	var bar = line.indexOf('|');
	var path = (bar == -1) ? line : truncsp(line.slice(0, bar));
	var label = (bar == -1)
		? file_getname(path).replace(/\.[^.]+$/, '')
		: line.slice(bar + 1).replace(/^\s+/, "");
	files.push(path);
	items.push({ header: false, label: label, num: files.length });
}

if(files.length < 1) {
	alert("No bulletins listed in " + file.name);
	exit(0);
}

// Display menu, list bulletins, display prompt, etc.

while(bbs.online && !js.terminated) {
	console.clear(LIGHTGRAY);
	console.print("\x01n\x01h\x01r===============================================================================\x01n\r\n");
	console.print("\r\n");
	console.print("\x01n\x01h\x01m                   __                 _ _                _\x01n\r\n");
	console.print("\x01n\x01h\x01m                  / _\xb3 ___   ___   __\xb3 \xb3 \xb3__   __ _ _ __\xb3 \xb3 __\x01n\r\n");
	console.print("\x01n\x01h\x01m                 \xb3 \xb3_ / _ \\ / _ \\ / _` \xb3 '_ \\ / _` \xb3 '__\xb3 \xb3/ /\x01n\r\n");
	console.print("\x01n\x01h\x01m                 \xb3  _\xb3 (_) \xb3 (_) \xb3 (_\xb3 \xb3 \xb3_) \xb3 (_\xb3 \xb3 \xb3  \xb3   <\x01n\r\n");
	console.print("\x01n\x01h\x01m                 \xb3_\xb3  \\___/ \\___/ \\__,_\xb3_.__/ \\__,_\xb3_\xb3  \xb3_\xb3\\_\\\x01n\r\n");
	console.print("\r\n");
	console.print("\x01n\x01h\x01y                            B u l l e t i n s                                   \x01n\r\n");
	console.print("\x01n\x01h\x01r-------------------------------------------------------------------------------\x01n\r\n");
	console.print("\r\n");
	for(i = 0; i < items.length; ++i) {
		if(items[i].header) {
			console.print("\x01n\x01h\x01m  " + items[i].text + "\r\n");
			console.print("\x01n\x01h\x01k  " +
				new Array(items[i].text.length + 1).join("-") + "\x01n\r\n");
			continue;
		}
		var num = "" + items[i].num;
		if(num.length < 2)
			num = " " + num;
		console.print("\x01n\x01h\x01y  " + num + "\x01n\x01w  " + items[i].label + "\r\n");
	}
	console.print("\r\n");
	console.mnemonics("\x01n\x01wEnter number or [\x01h\x01yQ\x01n\x01wuit]: ");
	b = console.getnum(files.length);
	if(b < 1)
		break;
	if(b > files.length) {
		alert("Invalid bulletin number: "+b);
	} else {
		console.clear(7);
		var fname = truncsp(files[b - 1]);
		var ext = file_getext(fname);
		var success = false;
		if(ext == ".*")
			success = bbs.menu(fname.slice(0, -2), p_mode);
		else if(fname.search(/\.htm/)!=-1)
			success = load(new Object, "typehtml.js", "-color", fname);		
		else
			success = console.printfile(fname, p_mode);
		if(success)
			log("viewed bulletin #" + b + ": "+fname);
		else
			log(LOG_WARNING, "Failed to view bulletin #" + b + " (" + fname + " is missing?)");
		console.aborted=false;
	}
}
