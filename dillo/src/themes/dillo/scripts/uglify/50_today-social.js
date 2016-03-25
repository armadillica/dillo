$(document).ready(function() {
	$('#social-toggle').click(function(){
		var pops = $('a');

		if ($(this).hasClass('activato')){
			$(this).removeClass('activato');
			$(this).html('<i class="di-share"></i>');

			$('#social').find(pops).each(function(i){
				$(this).animate({'right' : (5 * i) * -1, 'opacity' : 0});
			});

		} else {
			$(this).addClass('activato');

			$('#social').find(pops).each(function(i){
				$(this).animate({'right' : 40 * i, 'opacity' : 1.0});
			});

			$(this).html('<i class="di-cancel"></i>');
		};
	}); // social-toggle
});
