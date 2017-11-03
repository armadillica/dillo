function updateRatings() {
	// Fetch all ratings for the user and swap them in
	// TODO only update, remove and add what is needed
	// TODO rely on websockets to perform this operations
	$.get('/ratings', function(data) {
		// console.log('Getting ratings')
	})
		.done(function(data) {
			// Iterate over all local keys
			for (var i = 0; i < localStorage.length; i++){
				var key = localStorage.key(i);
				// Look for all dillo keys
				if (key.startsWith('dillo_')) {
					var key_split = key.split('_')[1];
					// Find a match from the server-provided ratings
					var rating_value = data.items[key_split]
					if (rating_value) {
						// If there is match, update the key
						localStorage.setItem(key, rating_value);
						delete data.items[key_split];
					} else {
						// Remove the key, since the user removed is vote
						localStorage.removeItem(key);
					}
				}
			}
			$.each(data.items, function(index, value) {
				var key = 'dillo_' + index;
				localStorage.setItem(key, value);
			});
		})
}

updateRatings();
