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


// Utility for delaying a function call (used to throttle keydown events)
var delay = (function () {
	var timer = 0;
	return function (callback, ms) {
		clearTimeout(timer);
		timer = setTimeout(callback, ms);
	};
})();


// Clicking on this class will display the dropdown-menu inside
$('.wgt-dropdown-toggle').on('click', function(e){
	$(this)
		.toggleClass('active')
		.find('.dropdown-menu')
		.toggleClass('active');
});
