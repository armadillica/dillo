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

function shortenUrl(url){

	if (typeof url !== 'undefined')
		url = url.replace('http://','').replace('https://','').replace('www.','').split(/[/?#]/)[0];

	return url;
}
