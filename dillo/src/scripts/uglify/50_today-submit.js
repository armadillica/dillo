$(document).ready(function() {
	var csrftoken = $('meta[name=csrf-token]').attr('content');

	$.ajaxSetup({
		beforeSend: function(xhr, settings) {
			if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
				xhr.setRequestHeader("X-CSRFToken", csrftoken)
			}
		}
	});


	$("#submit_post_form").on("submit", function (e) {

			e.preventDefault();

			// Let us know submission is in progress
			$('.post-submit-field-submit').html('<i class="fa fa-spinner fa-spin"></i> <i>Submitting...</i>');

			var data = $(this).serialize();
			var url = $(this).attr('action');
			var formData = new FormData($(this)[0]);
			$.ajax({
						url: url,
						type: 'POST',
						data: formData,
						processData: false,
						contentType: false,
						cache: false
					})
			.done(function(data){

				// All went just fine! Let's see the post
				$('.post-submit-field-submit').removeClass('houston');
				$('.post-submit-field-submit').addClass('success');
				$('.post-submit-field-submit').html('<i class="fa fa-check"></i> Success!');
				window.location.replace(data['post_url']);

			})
			.fail(function(data){

				// Problem found!
				$('.post-submit-field-submit').addClass('houston');
				$('.post-submit-field-submit').html('<i class="fa fa-frown-o fa-spin"></i> Houston! Try again?');

			});
	});

	(function() {
		var dlgtrigger = document.querySelector( '[data-dialog]' );
		var somedialog = document.getElementById( dlgtrigger.getAttribute( 'data-dialog' ) );
		var dlg = new DialogFx( somedialog );
		// var dlgtrigger = document.querySelector( '[data-dialog]' ),
		//   somedialog = document.getElementById( dlgtrigger.getAttribute( 'data-dialog' ) ),
		//   dlg = new DialogFx( somedialog );
		dlgtrigger.addEventListener( 'click', dlg.toggle.bind(dlg) );
	})();

	// CKEditor Stuff
	CKEDITOR.replace( 'post_content', {
		customConfig: '/static/js/ckeditor/config.js',
	});

	CKEDITOR.instances['post_content'].on('change', function() {
		CKEDITOR.instances['post_content'].updateElement()
	});

	// Change type of submission
	$('.select-change').click(function(){
		$('#post_type_id').val($(this).data('val'));

		$('.select-change').each(function(){
			$(this).removeClass('activato');
		});

		$(this).addClass('activato');

		$('.post-submit-div-title').show();
		$('.post-submit-div-category').show();
		$('.post-submit-div-picture').show();
		$('.post-submit-div-submit').show();

		// if ($('#post_picture_remote').val() != ''){
		//   $('.post-submit-div-picture').hide();
		// };

		if ($('#post_type_id').val() == 1){

			$('.post-submit-link').show();
			$('.post-submit-article').hide();

			$('#url').focus()

			$('.post-submit-field-submit').addClass('disabled');

		};

		if ($('#post_type_id').val() == 2){

			$('.post-submit-link').hide();
			$('.post-submit-article').show();

			$('#title').focus()

			$('.post-submit-field-submit').removeClass('disabled');

		};
	}); // change type of submission

});
