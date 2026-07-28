/*	foodbark-art.js - show BBS ANSI art as images in the web forum.

	Articles posted by mods/exec/post_foodbark.js embed truecolor half-block
	ANSI in the message body. That is right for the terminal and unusable in a
	browser: Synchronet's html_encode predates 24-bit colour and mis-parses it
	(leaking fragments like "2;0;40;120m" into the page), and stock webv4
	strips ANSI escapes without stripping the half-block characters, so a
	56KB message renders as ~1600 naked block bytes above the essay.

	So the poster wraps each piece of art in plain-ASCII sentinels naming its
	image, and this replaces the whole marked block with that image:

	    [art:stand-up-soba-1]  ...anything at all...  [/art]
	        ->  <img src="./images/foodbark/stand-up-soba-1.png">

	The PNG is decoded straight back out of the same .ans by
	scripts/foodbark_art.py, so it is pixel-identical to what a terminal
	paints. Same image, drawn by the browser instead of SyncTERM.

	Loaded from webv4/mods/components/header.xjs, which is an override hook,
	so no stock file is forked. Messages arrive asynchronously as the reader
	clicks around, hence the MutationObserver rather than a one-shot pass.
*/
(function () {
	'use strict';

	var IMG_BASE = './images/foodbark/';
	// Sentinels are plain ASCII so they survive the server-side ANSI strip.
	// [\s\S] because the mangled art in between spans many lines, and the
	// lazy quantifier so two images in one message do not merge into one.
	var BLOCK = /\[art:([A-Za-z0-9._-]+)\][\s\S]*?\[\/art\]/g;
	// A name must not escape the image directory.
	var SAFE = /^[A-Za-z0-9._-]+$/;

	function swap(el) {
		if (!el || el.getAttribute('data-fb-art') === 'done') return;
		var html = el.innerHTML;
		// Empty means the body has not been injected yet. Leave it unmarked
		// so it gets picked up on the mutation that fills it in.
		if (!html) return;
		if (html.indexOf('[art:') === -1) {
			el.setAttribute('data-fb-art', 'done');
			return;
		}

		var changed = false;
		html = html.replace(BLOCK, function (whole, name) {
			if (!SAFE.test(name) || name.indexOf('..') !== -1) return whole;
			changed = true;
			return '<img class="fb-art" loading="lazy" alt="ANSI art: ' +
			       name + '" src="' + IMG_BASE + name + '.png">';
		});

		el.setAttribute('data-fb-art', 'done');
		if (changed) {
			el.innerHTML = html;
			swapped++;
			console.info('foodbark-art: replaced art in #' + (el.id || '?'));
		}
	}

	// webv4 has TWO forum templates and they use different markup:
	//
	//   pages/001-forum.ssjs  server-renders into <div class="message" id=..>
	//                         and is the one the nav actually links to
	//   pages/001-forum.xjs   client-fills <div class="message"
	//                         data-message-body> via xjs-forum.js
	//
	// Match both. Targeting only data-message-body silently does nothing on
	// the server-rendered page, which is the page most people see.
	var SELECTOR = '[data-message-body]:not([data-fb-art]),' +
	               'div.message:not([data-fb-art])';

	// Always scan from the document rather than from mutation.addedNodes.
	// The .xjs path assigns innerHTML on an EXISTING div, so the added nodes
	// are that div's children and never the div itself. Re-querying is cheap
	// because the done-marker makes an already-processed body an O(1) skip.
	var swapped = 0;

	function scan() {
		var nodes = document.querySelectorAll(SELECTOR);
		for (var i = 0; i < nodes.length; i++) swap(nodes[i]);

		// Diagnostic. If the markers are on the page but no container matched,
		// the selector is wrong for whichever template rendered it, and that
		// is invisible from the server side.
		if (!swapped && document.body &&
		    document.body.textContent.indexOf('[art:') !== -1) {
			console.warn('foodbark-art: found [art:] markers but matched no ' +
			             'message container. Selector needs updating for this ' +
			             'template.');
		}
	}

	function start() {
		scan();
		if (typeof MutationObserver !== 'function') return;
		var queued = false;
		new MutationObserver(function () {
			// swap() writes innerHTML, which fires this observer again. The
			// done-marker stops that recursing, and coalescing per frame
			// keeps a long thread from rescanning once per inserted node.
			if (queued) return;
			queued = true;
			(window.requestAnimationFrame || window.setTimeout)(function () {
				queued = false;
				scan();
			}, 0);
		}).observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', start);
	} else {
		start();
	}
})();
