$(document).ready(function() {
 	$('.post-title-url').each(function(){
		var link = $(this).text();
		var pretty = link.replace(/.*?:\/\//g, "").replace(/^www./, "").replace(/\/$/, "");
		var prettier = pretty.substr(0, pretty.indexOf('/'))
		if (prettier != ''){
			$(this).text(prettier);
		} else {
			$(this).text(pretty);
		};
		$(this).css('visibility', 'visible');
	});
});
