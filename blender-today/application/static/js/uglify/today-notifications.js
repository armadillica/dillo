// Notifications

function getnotifications(){
	$.getJSON( "/notifications", function( data ) {

		var items = [];
		var unread_ctr = 0;

		$.each(data['items'], function(i, no){

			// Increase the unread_ctr counter
			if (!no['is_read']){ unread_ctr++ };

			// Check if the current item has been read,
			// so we can style it nicely
			is_read = no['is_read'] ? 'is_read' : '';

			// List item
			content = '<li class="nc-item ' + is_read +'">';

				// Avatar linking to username profile
				content += '<div class="nc-avatar">';
					content += '<a href="' + no['username_url'] + '">';
					content += '<img src="' + no['username_avatar'] + '"/> ';
					content += '</a>';
				content += '</div>';

				// Text of the notification
				content += '<div class="nc-text">';

					// Username
					content += '<a href="' + no['username_url'] + '">' + no['username'] + '</a> ';

					// Action
					content += no['action'] + ' ';

					// Object
					content += '<a href="' + no['object_url'] + '">';
						content += no['context_object_name'] + ' ';
					content += '</a> ';

					// Date
					content += '<span class="nc-date">';
						content += '<a href="' + no['object_url'] + '">' + no['date'] + '</a>';
					content += '</span>';

				content += '</div>';
			content += '</li>';

			items.push(content);
		});

		if (unread_ctr > 0) {
			// Set page title, display notifications and set counter
			document.title = '(' + unread_ctr + ') ' + page_title;
			$('#notifications-count').addClass('bloom');
			$('#notifications-count').text(unread_ctr);
		};

		// Populate the list
		$('#notifications-list').html( items.join('') );
	});
};

function hideNotifications(){
	$('#notifications').hide();
	$('#notifications-toggle').removeAttr('class');
};

// Click anywhere in the page to hide the #notifications
$(document).click(function() { hideNotifications(); });

// Toggle the #notifications flyout
$('#notifications-toggle').on('click', function(e){
	e.stopPropagation();
	$('#notifications').toggle();
	$(this).toggleClass("active");
});

// Clicking inside the #notifications flyout shouldn't hide it
$('#notifications').on('click', function(e){ e.stopPropagation(); });

getnotifications();
