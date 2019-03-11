function ValidURL(str) {
	// RegExp by https://gist.github.com/dperini/729294
	var pattern = new RegExp(
		"^" +
		// protocol identifier
		"(?:(?:https?|ftp)://)" +
		// user:pass authentication
		"(?:\\S+(?::\\S*)?@)?" +
		"(?:" +
		// IP address exclusion
		// private & local networks
		"(?!(?:10|127)(?:\\.\\d{1,3}){3})" +
		"(?!(?:169\\.254|192\\.168)(?:\\.\\d{1,3}){2})" +
		"(?!172\\.(?:1[6-9]|2\\d|3[0-1])(?:\\.\\d{1,3}){2})" +
		// IP address dotted notation octets
		// excludes loopback network 0.0.0.0
		// excludes reserved space >= 224.0.0.0
		// excludes network & broacast addresses
		// (first & last IP address of each class)
		"(?:[1-9]\\d?|1\\d\\d|2[01]\\d|22[0-3])" +
		"(?:\\.(?:1?\\d{1,2}|2[0-4]\\d|25[0-5])){2}" +
		"(?:\\.(?:[1-9]\\d?|1\\d\\d|2[0-4]\\d|25[0-4]))" +
		"|" +
		// host name
		"(?:(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)" +
		// domain name
		"(?:\\.(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)*" +
		// TLD identifier
		"(?:\\.(?:[a-z\\u00a1-\\uffff]{2,}))" +
		// TLD may end with dot
		"\\.?" +
		")" +
		// port number
		"(?::\\d{2,5})?" +
		// resource path
		"(?:[/?#]\\S*)?" +
		"$", "i"
	);
	if (!pattern.test(str)) {
		if (console) console.log("Please enter a valid URL.");
		return false;
	} else {
		return true;
	}
}

/* urlParams, by Andy E on https://stackoverflow.com/a/2880929 */
var urlParams;
(window.onpopstate = function () {
	var match,
			pl     = /\+/g,  // Regex for replacing addition symbol with a space
			search = /([^&=]+)=?([^&]*)/g,
			decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); },
			query  = window.location.search.substring(1);

	urlParams = {};

	while (match = search.exec(query))
		urlParams[decode(match[1])] = decode(match[2]);
})();


/*
 * XXX Quick hack to silence the error when getting typeahead
 * Typeahead is a library used by global search in Pillar.
 * Since Dillo uses instantsearch, not global, we don't need it.
 * But silly Pillar doesn't know yet, a proper fix will come later.
*/
(function ($) {
	$.fn.typeahead = function() {};
}(jQuery));


/* Cleanup the URL to just have the domain, without WWW. */
function parse_hostname(url) {
	var anchor = document.createElement('a');
	anchor.href = url;

	var hostname = anchor.hostname;
	hostname = hostname.replace(/^www./, "");

	return hostname;
}
