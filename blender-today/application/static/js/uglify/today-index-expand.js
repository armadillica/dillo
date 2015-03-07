$(document).ready(function() {
 	$('.post-index-item-picture-expand').click(function(){
		$(this).next($('.post-index-item-picture')).attr('src', $(this).next().data('rel'));
		$(this).next($('.post-index-item-picture')).css('display', 'block');
		$(this).next($('.post-index-item-picture')).animate({'opacity': 1.0});
		$(this).fadeOut('fast', function(){
			$(this).prev().fadeIn('fast');
		});
	});

	$('.post-index-item-picture-collapse').click(function(){
		$(this).next().next().fadeOut('fast');
		$(this).fadeOut('fast', function(){
			$(this).next().fadeIn('fast');
		});
	});

	$('.post-index-item-picture').mousedown(function(e){
		e.preventDefault();

		image = $(this);

		$(document).mousemove(function(e){
			e.preventDefault();
			var x = ((e.pageX - image.parent().offset().left) + (image.width())) * 0.6;
			$(image).css("width", x);
		})
	});

	$(document).mouseup(function(e){
		$(document).unbind('mousemove');
	});
});
