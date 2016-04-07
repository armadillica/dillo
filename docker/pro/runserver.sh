#!/bin/bash

# Run setup if installed flag is not found
if [ ! -e /installed ]; then
	# Generate a basic config.py so that dillo can be started
	SECURITY_PASSWORD_SALT="$(date +%s | sha256sum | base64 | head -c 32 ; echo)"
	SECRET_KEY="$(date +%s | sha256sum | base64 | head -c 32 ; echo)"
	cp /data/git/dillo/dillo/config.py.sample /data/git/dillo/dillo/config.py
	sed -i "s/__SECURITY_PASSWORD_SALT/${SECURITY_PASSWORD_SALT}/g" /data/git/dillo/dillo/config.py
	sed -i "s/__SECRET_KEY/${SECRET_KEY}/g" /data/git/dillo/dillo/config.py
	# Start migration
	. /data/venv/bin/activate && python /data/git/dillo/dillo/manage.py db upgrade --directory=/data/git/dillo/dillo/migrations/
	# Create admin user
	. /data/venv/bin/activate && python /data/git/dillo/dillo/manage.py setup
	npm install -g gulp
	cd /data/git/dillo && npm install
	gulp
	cd /

	touch /installed
fi

# Run Apache
/usr/sbin/apache2ctl -D FOREGROUND
