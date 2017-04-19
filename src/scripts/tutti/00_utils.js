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
