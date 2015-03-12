$(document).ready(function() {
 	$('.post-title-url').each(function(){
		var link = $(this).text();
		var pretty = link.replace(/.*?:\/\//g, "").replace(/^www./, "").replace(/\/$/, "");
		var prettier = pretty.substr(0, pretty.indexOf('/'))
		$(this).text(prettier);
		$(this).css('visibility', 'visible');
	});
});
