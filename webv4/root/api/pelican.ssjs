/*	pelican.ssjs - Web chat endpoint for The Pelican.

	Logged-in users only. Guests get a 401 and the page tells them to log in.
	The board is small and private, but this endpoint spends real API money on
	every call, so it is never open to anonymous traffic and every user is
	capped per day.

	The persona, knowledge files and the Claude call itself live in
	mods/load/pelican_brain.js, shared with the terminal module mods/pelican.js.
	History is deliberately the SAME file the terminal writes
	(data/user/pelican_NNNN.json), so a conversation carries across venues.

	GET                     -> { ok, alias, remaining, history: [{role, content}] }
	POST { message: "..." } -> { ok, reply, remaining }
	POST { greet: true }    -> same, sends the silent "HELLO" opener
*/

var settings = load('modopts.js', 'web') || { web_directory: '../webv4' };

load(settings.web_directory + '/lib/init.js');
load(settings.web_lib + 'auth.js');
load(system.mods_dir + 'load/pelican_brain.js');

var brain = PelicanBrain;

function reply(obj, status) {
	var body = JSON.stringify(obj);
	if (status) http_reply.status = status;
	http_reply.header['Content-Type'] = 'application/json';
	http_reply.header['Content-Length'] = body.length;
	http_reply.header['Cache-Control'] = 'no-store';
	write(body);
	exit();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

if (user.alias === settings.guest || user.number === 0) {
	reply({ ok: false, error: 'auth', message: 'Log in and she will talk to you.' },
	      '401 Unauthorized');
}

// ── Per-user daily cap ────────────────────────────────────────────────────────
// Kept in its own file so pelican_NNNN.json stays a plain history array that
// the terminal module can keep reading.

var quota_path = system.data_dir + 'user/pelican_webquota_' +
	format('%04d', user.number) + '.json';

function today() {
	var d = new Date();
	return d.getFullYear() + '-' + format('%02d', d.getMonth() + 1) + '-' +
		format('%02d', d.getDate());
}

function read_quota() {
	var f = new File(quota_path);
	if (!f.open('r', true)) return { day: today(), count: 0 };
	var raw = f.read();
	f.close();
	try {
		var q = JSON.parse(raw);
		if (q && q.day === today()) return q;
	} catch (e) {}
	return { day: today(), count: 0 };
}

function write_quota(q) {
	var f = new File(quota_path);
	if (f.open('w', true)) {
		f.write(JSON.stringify(q));
		f.close();
	}
}

var quota = read_quota();
var limit = brain.config.web_daily_limit;

// ── GET: hand back the running conversation ───────────────────────────────────

if (http_request.method !== 'POST') {
	var hist = brain.load_history(user.number).filter(function (m) {
		// "HELLO" is the silent opener both front ends send; the user never
		// saw it on screen, so it should not appear in the transcript.
		return !(m.role === 'user' && m.content === 'HELLO');
	});
	reply({
		ok: true,
		alias: user.alias,
		remaining: Math.max(0, limit - quota.count),
		history: hist
	});
}

// ── POST: say something to her ────────────────────────────────────────────────

var payload;
try {
	payload = JSON.parse(http_request.post_data);
} catch (e) {
	reply({ ok: false, error: 'bad_request' }, '400 Bad Request');
}

var message = payload.greet ? 'HELLO' : ('' + (payload.message || ''));

// Strip control characters; keep tabs and newlines out of it entirely.
message = message.replace(/[\x00-\x1f\x7f]/g, ' ').replace(/^\s+|\s+$/g, '');

if (!message) {
	reply({ ok: false, error: 'empty' }, '400 Bad Request');
}

if (message.length > brain.MAX_INPUT) {
	reply({ ok: false, error: 'too_long',
	        reply: 'Keep it under ' + brain.MAX_INPUT + ' characters, sugar. *squawk*' });
}

if (brain.is_injection(message)) {
	reply({ ok: true, filtered: true,
	        reply: "Hon, I've been around long enough to know a con when I see one. *squawk*",
	        remaining: Math.max(0, limit - quota.count) });
}

if (quota.count >= limit) {
	reply({ ok: false, error: 'quota',
	        reply: "That's enough chattin for one day, darlin. Come find me tomorrow. *squawk*",
	        remaining: 0 });
}

var history = brain.load_history(user.number);
var res = brain.ask(history, message, { venue: 'web' });

if (!res.ok) {
	log(LOG_WARNING, 'Pelican web chat failed for ' + user.alias + ': ' + res.error);
	reply({ ok: false, error: 'upstream',
	        reply: 'Something went sideways, hun. Try again?' },
	      '502 Bad Gateway');
}

brain.save_history(user.number, history);

quota.count++;
write_quota(quota);

reply({
	ok: true,
	reply: res.text,
	remaining: Math.max(0, limit - quota.count)
});
