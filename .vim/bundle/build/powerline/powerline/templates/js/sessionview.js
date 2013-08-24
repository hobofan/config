var session_viewer = {
	setup: function() {
		session_viewer.update_url = '/sessions'

		session_viewer.update_sessions()
		setInterval('session_viewer.update_sessions()', 10000)
	},
	
	update_sessions: function() {
		$.getJSON('/sessions', function(json) {
			json = json.result
			results = ''
			for (i = 0; i < json.length; i++) {
				session = json[i];
				result = '<li class="' + (session.start_time != null ? 'logged-on' : 'waiting') + '">Ticket <strong>';
				result += '#' + json[i].daily_id + '</strong> ';
				if (session.start_time == null) {
					if (session.line_position != 0) {
						result += ' (' + session.line_position + ' in line)';
					} else {
						result += 'ready to get on';
					}
				} else {
					result += 'is currently on';
				}
				result += '</li>';
				results += result + '</li>';
			}
			$('#sessions ul').html(results);
		});
	}
}

jQuery(document).ready(function(){
	session_viewer.setup();
});
