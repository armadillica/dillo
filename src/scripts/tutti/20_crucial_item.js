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
	.fail(function(xhr, status, error) {

		setMessage(xhr);
	});
});
