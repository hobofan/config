CREATE TABLE users (
	username VARCHAR(255) PRIMARY KEY,
	allowed_after DATE NOT NULL DEFAULT '1970-01-01' -- For banning and barring
);

CREATE TABLE systems (
	name VARCHAR(255) PRIMARY KEY, -- The internal name; used by the client
	title VARCHAR(255) NOT NULL -- The title of the system; what is actually displayed
);

CREATE TABLE settings (
	name VARCHAR(255) PRIMARY KEY,
	value VARCHAR(255),
	type VARCHAR(255) -- See powerline/manager.py for a list of valid types
);
INSERT INTO settings VALUES ('session_time', '35', 'int');
INSERT INTO settings VALUES ('overrides', 'override', 'list');
INSERT INTO settings VALUES ('hours', '00:00-00:00,00:00-00:00,00:00-00:00,00:00-00:00,00:00-00:00,00:00-00:00,00:00-00:00', 'list');
INSERT INTO settings VALUES ('sessions_per_user', '4', 'int');
INSERT INTO settings VALUES ('manager_users', 'admin:', 'list');
INSERT INTO settings VALUES ('session_expire_time', '5', 'int');
INSERT INTO settings VALUES ('reservation_entry_prefill', '', 'none');

-- The session log.
-- Note that this contains all sessions, including unstarted and ended ones.
CREATE TABLE sessions (
	session_id INTEGER PRIMARY KEY AUTO_INCREMENT,
	daily_id INTEGER NOT NULL, -- An id number with a sequence that restarts daily.
	user VARCHAR(255) NOT NULL,
	system VARCHAR(255),
	start_time DATETIME,
	end_time DATETIME,
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
