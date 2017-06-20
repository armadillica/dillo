(function ( $ ) {
	/*
	 * jQuery autoResize (textarea auto-resizer)
	 * @copyright James Padolsey http://james.padolsey.com
	 * @version 1.04
	 * cracked by icyleaf <icyleaf.cn@gmail.com>
	 * https://gist.github.com/icyleaf/269160
	 */
	$.fn.autoResize = function(options) {
		var settings = $.extend({
			onResize : function(){},
			animate : true,
			animateDuration : 0,
			animateCallback : function(){},
			extraSpace : 20,
			limit: 500
		}, options);

		this.filter('textarea').each(function(){
			var textarea = $(this).css({resize:'none','overflow-y':'hidden'}),
			origHeight = textarea.height(),
			clone = (function(){
				var props = ['height','width','lineHeight','textDecoration','letterSpacing'],
					propOb = {};

				$.each(props, function(i, prop){
					propOb[prop] = textarea.css(prop);
				});

				return textarea.clone().removeAttr('id').removeAttr('name').css({
					position: 'absolute',
					top: 0,
					left: -9999
				}).css(propOb).attr('tabIndex','-1').insertBefore(textarea);
			})(),
			lastScrollTop = null,
			updateSize = function() {

				clone.height(0).val($(this).val()).scrollTop(10000);
				var scrollTop = Math.max(clone.scrollTop(), origHeight) + settings.extraSpace,
					toChange = $(this).add(clone);

				if (lastScrollTop === scrollTop) { return; }
				lastScrollTop = scrollTop;

				if ( scrollTop >= settings.limit ) {
					if ( settings.limit != 0) {
						$(this).css('overflow-y','').css('height', settings.limit+'px');
						return;
					}
				}
				settings.onResize.call(this);
				settings.animate && textarea.css('display') === 'block' ?
					toChange.stop().animate({height:scrollTop}, settings.animateDuration, settings.animateCallback)
					: toChange.height(scrollTop);
			};
			textarea
				.unbind('.dynSiz')
				.bind('keyup.dynSiz', updateSize)
				.bind('keydown.dynSiz', updateSize)
				.bind('change.dynSiz', updateSize)
				.bind('blur.dynSiz', updateSize);
		});
		return this;
	};

}(jQuery));

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
