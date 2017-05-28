/* Open posts on the side */
function item_open(item_id){

	if (item_id === undefined) {
		throw new ReferenceError("item_open(" + item_id + ") called.");
	}

	var item_url = '/nodes/' + item_id + '/view';

	$.get(item_url, function(item_data) {

		$('#list-item').html(item_data);

	}).fail(function(xhr) {
		if (console) {
			console.log('Error fetching item', item_id, 'from', item_url);
			console.log('XHR:', xhr);
		}

		setMessage(xhr);
	});
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
	})
	.fail(function(xhr) {

		setMessage(xhr);
	});
});


/* Post type tab switching */
$(document).on('click','body ul.item-edit-tabs li',function(e){
	var post_type = $(this).data('post-type');
	var $tab = $('#item-edit-tab');

	$('.item-edit-tab select.post_type').val(post_type).change();
	$('.item-edit-tab select.post_type options[value=' + post_type + ']').attr('selected', 'selected');

	// console.log($('.item-edit-tab.' + post_type + ' select.post_type').val());

	$('ul.item-edit-tabs li').removeClass('active');
	$(this).addClass('active');

	$tab
		.removeClass('text link')
		.addClass(post_type);
});
