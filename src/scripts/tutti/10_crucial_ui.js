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


// Context Workflow
// Save current context as prev-context and set new one
function setContext(context_type){
	ProjectUtils.setProjectAttributes({prevContext: ProjectUtils.context()});
	ProjectUtils.setProjectAttributes({context: context_type});
}

// Set previous context as current
function unsetPreviousContext(){

	var currContext = ProjectUtils.context();
	var previousContext = $('body').attr('data-prev-context');

	if (previousContext){
		ProjectUtils.setProjectAttributes({prevContext: currContext });
		ProjectUtils.setProjectAttributes({context: previousContext });
	}
}


// Fullscreen Workflow
function enterFullscreen(){
	$('a.wgt-toggle-fullscreen').addClass('active');
	$('#col_right').addClass('fullscreen');

	setContext("post-fullscreen");
}

function exitFullscreen(){
	$('a.wgt-toggle-fullscreen').removeClass('active');
	$('#col_right').removeClass('fullscreen');

	unsetPreviousContext();

	if ($('body').hasClass('posts-index')){
		setContext("posts-index");
	} else if ($('body').hasClass('post-edit')) {
		setContext("post-edit");
	}
}

function toggleFullscreen(){
	if (ProjectUtils.context() == 'post-fullscreen'){
		exitFullscreen();
	} else {
		enterFullscreen();
	}
}

$('a.wgt-toggle-fullscreen').on('click', function(){
	toggleFullscreen();
});


// Submit Dialog Workflow
function enterSubmit(){
	$.get("/post/link?embed=1", function(data) {
		$('.dialog-box').html(data);
	});
	$('#app-overlay').addClass('active submit');
	setContext("post-submit-overlay");

	Mousetrap.unbind('f');
}

function exitSubmit(){
	$('#app-overlay').removeAttr('class');
	unsetPreviousContext();

	initializeShortcuts();
}

function toggleSubmit(){
	if (ProjectUtils.context() == 'post-submit-overlay'){
		exitSubmit();
	} else {
		enterSubmit();
	}
}

$('a.wgt-toggle-submit').on('click', function(){
	toggleSubmit();
});


// Initialize Shortcuts
function initializeShortcuts(){
	Mousetrap.bind('f', toggleFullscreen);
	Mousetrap.bind('s', toggleSubmit);

	Mousetrap.bind('esc', function(e) {
		if (ProjectUtils.context() == 'post-submit-overlay'){
			exitSubmit();
		} else if (ProjectUtils.context() == 'post-fullscreen'){
			exitFullscreen();
		}
	});
}

initializeShortcuts();
