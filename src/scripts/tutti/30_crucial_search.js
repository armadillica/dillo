function updateRatings() {
	// Fetch all ratings for the user and swap them in
	// TODO only update, remove and add what is needed
	// TODO rely on websockets to perform this operations
	$.get('/ratings', function(data) {
		// console.log('Getting ratings')
	})
		.done(function(data) {
			$.each(data.items, function(index, value) {
				localStorage.setItem(value[0], value[1]);
			});
		})
}

updateRatings();
