var global_container = document.getElementById('app-main');

function containerResizeY(window_height){

	var height = window_height - global_container.offsetTop;

	if (typeof global_container !== "undefined"){
		$(global_container).css(
			{
				'height': height + 'px',
				'max-height': height + 'px'
			}
		);
	}
}

/* UI Stuff */
$(window).on("load resize",function(){
	containerResizeY(window.innerHeight);
});
