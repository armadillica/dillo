/* UI Stuff */
var global_container = document.getElementById('app-main');

function containerResizeY(window_height){

	var height = window_height - global_container.offsetTop;

	$('#app-main, #col_main, #col_right').css({
		'height': height + 'px',
		'max-height': height + 'px'
	});
}

$(window).on("load resize",function(){
	containerResizeY(window.innerHeight);
});


/* Post type tab switching */
$(document).on('click','body ul.item-edit-tabs li',function(e){
	var post_type = $(this).data('post-type');

	$('.item-edit-tab.' + post_type + ' select.post_type').val(post_type).change();
	$('.item-edit-tab.' + post_type + ' select.post_type options[value=' + post_type + ']').attr('selected', 'selected');

	// console.log($('.item-edit-tab.' + post_type + ' select.post_type').val());

	$('ul.item-edit-tabs li, .item-edit-tab').removeClass('active');

	$(this).addClass('active');
	$('.item-edit-tab.' + post_type).addClass('active');
});

function setMessage(xhr){
	popNotification();

	$('#notification-pop').addClass('code-' + xhr.status);

	// The text in the pop
	var text = '<span class="nc-author">' + xhr.status + ' ' + xhr.statusText + '</span> ';
	$('#notification-pop .nc-text').html(text);
}

function shortenUrl(url){
	url = url.replace('http://','').replace('https://','').replace('www.','').split(/[/?#]/)[0];

	return url;
}
