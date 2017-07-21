/* Open posts on the side */
function item_open(item_id, hit_url){
	if (item_id === undefined) {
		throw new ReferenceError("item_open(" + item_id + ") called.");
	}

	var item_url = '/nodes/' + item_id + '/view';

	//if (typeof push_url == 'undefined') push_url = item_url;

	$.get(item_url, function(item_data) {

		$('#list-item').html(item_data);

	}).fail(function(xhr) {
		if (console) {
			console.log('Error fetching item', item_id, 'from', item_url);
			console.log('XHR:', xhr);
		}

		toastr.error(xhr.statusText, 'Error ' + xhr.status);
	});

	if (hit_url === undefined) {
		return;
	}

	// Determine whether we should push the new state or not.
	pushState = (typeof pushState !== 'undefined') ? pushState : true;
	if (!pushState) return;

	// Push the correct URL onto the history.
	var push_state = {itemId: item_id};

	window.history.pushState(
		push_state,
		item_id,
		hit_url
	);
}

/* Rate | Vote */
$(document).on('click','body .item-rating',function(e){
	e.preventDefault();

	var $this = $(this);
	var nodeId = $this.closest('.item-content').data('node-id');
	var is_positive = !$this.hasClass('down');
	var parentDiv = $this.parent();
	var rated_positive = parentDiv.hasClass('positive');

	if (typeof nodeId === 'undefined') {
		if (console) console.log('Undefined node ID');
		return;
	}

	var op;
	if (parentDiv.hasClass('rated') && is_positive == rated_positive) {
		op = 'revoke';
	} else if (is_positive) {
		op = 'upvote';
	} else {
		op = 'downvote';
	}

	$.post("/p/" + nodeId + "/rate/" + op)
	.done(function(data){

		// Add/remove styles for rated statuses
		switch(op) {
			case 'revoke':
				parentDiv.removeClass('rated positive negative');
				break;
			case 'upvote':
				parentDiv.addClass('rated positive');
				parentDiv.removeClass('negative');
				break;
			case 'downvote':
				parentDiv.addClass('rated negative');
				parentDiv.removeClass('positive');
				break;
		}

		var rating = data['data']['rating_positive'] - data['data']['rating_negative'];
		$this.siblings('.item-rating.value').text(rating);
		toastr.info('Voted!');
	})
	.fail(function(xhr) {
		toastr.error(xhr.statusText, 'Error ' + xhr.status);
	});
});


/* Post type tab switching */
$(document).on('click','body ul.item-edit-tabs li',function(e){
	var post_type = $(this).data('post-type');
	var $tab = $('#item-edit-tab');

	// Change the post_type select to the appropiate post_type
	$('.item-edit-tab select.post_type').val(post_type).change();
	$('.item-edit-tab select.post_type option').removeAttr('selected');
	$('.item-edit-tab select.post_type option[value="' + post_type + '"]').attr('selected', '');

	// Enable the 'content' field for the appropriate post_type, disable the others
	$('.input-content .input-field')
		.prop('disabled', true)
		.removeAttr('id');

	var $input_field = $('.input-content.' + post_type + ' .input-field');
	$input_field
		.prop('disabled', false)
		.attr('id', 'content');

	// Style the tab as active
	$('ul.item-edit-tabs li').removeClass('active');
	$(this).addClass('active');

	// Add the post_type class to the tab, to show/hide elements
	$tab
		.removeClass('text link')
		.addClass(post_type);


	/* Focus the cursor on the 'content' field */
	if (post_type == 'link'){
		$input_field.focus();
	}
});

/* UI: Update category on edit */
$('select#category').on('change', function(e){
	$('#item-category').text($(this).val());
});


/* Prompt when leaving a page with an input/textarea modified */
$('input, textarea').keypress(function () {
	// Set the beforeunload to warn the user of unsaved changes
	$(window).on('beforeunload', function () {
		return 'You have unsaved changes in your post.';
	});
});
