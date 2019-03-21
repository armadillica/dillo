var $displayToggleWidget = $('.wgt-display-mode-toggle');

// Browse type: icon or list
function postsViewModeTypeIcon() {
	$("#col_main").removeClass('cards-display');
	$displayToggleWidget.html('<i class="pi-layout m-0"></i>');
};

function postsViewModeTypeList() {
	$("#col_main").addClass('cards-display');
	$displayToggleWidget.html('<i class="pi-list m-0"></i>');
};

function postsViewModeTypeCheck(){
	/* Only run if we're in a project, or search */
	var browse_type = Cookies.getJSON('bcommunity_ui');

	if (browse_type && browse_type.group_browse_type) {
		if (browse_type.group_browse_type == 'icon') {
			postsViewModeTypeIcon();

		} else if ( browse_type.group_browse_type == 'list' ) {
			postsViewModeTypeList();
		}
	} else {
		postsViewModeTypeIcon();
	};
}

function postsViewModeToggle(){

	var browse_type = Cookies.getJSON('bcommunity_ui');

	if (browse_type && browse_type.group_browse_type) {
		if (browse_type.group_browse_type == 'icon') {
			postsViewModeTypeList();
			setJSONCookie('bcommunity_ui', 'group_browse_type', 'list');
		} else if ( browse_type.group_browse_type == 'list' ) {
			postsViewModeTypeIcon();
			setJSONCookie('bcommunity_ui', 'group_browse_type', 'icon');
		}
	} else {
		postsViewModeTypeList();
		setJSONCookie('bcommunity_ui', 'group_browse_type', 'list');
	}
}

$displayToggleWidget.on('click', function (e) {
	e.preventDefault();
	postsViewModeToggle();
});

postsViewModeTypeCheck();
