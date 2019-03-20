
/* Open posts on the side */
function item_open(item_id, hit_url){
	if (item_id === undefined) {
		throw new ReferenceError("item_open(" + item_id + ") called.");
	}

	var item_url = '/nodes/' + item_id + '/view';

	$('#list-item .item-body')
		.html('\
			<div class="item-loading"><i class="pi-spin spin"></i></div>\
		');

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
	var push_state = {nodeId: item_id, url: hit_url};
	var push_url = hit_url;

	window.history.pushState(
			push_state,
			'Node ' + item_id, // TODO: use sensible title
			hit_url
	);

	// It's not the first load anymore, utems should open on the side not fullscreen
	first_time = false;
}


window.onpopstate = function(event) {
	var state = event.state;

	if (state == null) {
		// Go back to the community
		// TODO: Use real url
		if ($('body').hasClass('main-project')){
			return window.location.href = '/c/';
		} else {
			return window.location.href = '/c/' + ProjectUtils.projectUrl();
		}
	}

	// Go back to a post
	item_open(state.nodeId, state.url)
};


/* Rate | Vote */
$(document).on('click','body .item-rating.up, body .item-rating.down',function(e){
	e.preventDefault();

	var $this = $(this);
	var nodeId = $this.closest('.item-content').data('node-id');
	var is_positive = !$this.hasClass('down');
	var parentDiv = $this.parent();
	var rated_positive = parentDiv.hasClass('positive');

	if (!isAuthenticated()){
		return window.location.href = '/login';
	}

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

		var rating = data['data']['rating_positive'] - data['data']['rating_negative'];

		// UI updates for the item on the list and the one in view_embed
		$('#item-' + nodeId + ', #' + nodeId).each(function(i) {

			// Update rating number
			$(this).find('.item-rating.value').text(rating);

			parentDiv = $(this).find('.item-rating-box');

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
		});

		toastr.info('Voted!');

		ga('send', 'event', 'vote', op);
	})
	.fail(function(xhr) {
		toastr.error(xhr.statusText, 'Error ' + xhr.status);

		ga('send', 'event', 'vote', 'failed');
	});
});


/* UI: Update category on edit */
$('select#category').on('change', function(e){
	$('#item-category').text($(this).val());
});


/* Prompt when leaving a page with an input/textarea modified in post edit mode */
if (ProjectUtils.context() == 'post-edit'){
	$('input, textarea').keypress(function () {
		// Set the beforeunload to warn the user of unsaved changes
		$(window).on('beforeunload', function () {
			return 'You have unsaved changes in your post.';
		});
	});
}


// Used on the index to open the post item
$('body').on('click', '.js-item-open', function(e){

	// If target has 'follow-link' class, follow the link!
	// Used for <a> pointing to external urls, like post_type link has
	if ($(e.target).hasClass('js-follow-link')) {
		return;
	}

	e.preventDefault();
	e.stopPropagation();

	var li = $(this).closest('.list-hits-item');
	var hit_id = li.attr('data-id');
	var hit_url = li.attr('data-url');

	/* Unstyle all items on the list and style only the current one */
	$('.list-hits-item').removeClass('active');
	li.addClass('active');

	item_open(hit_id, hit_url);

	ga('send', 'event', 'ui', 'open', $(this).attr('class'));
});
