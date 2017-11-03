#!/usr/bin/env bash

source /install_scripts.sh

# Make sure that log rotation works.
mkdir -p ${APACHE_LOG_DIR}
service cron start

if [ "$DEV" = "true" ]; then
    echo "Running in development mode"
    cd /data/git/dillo
    exec bash /manage.sh runserver --host='0.0.0.0'
else
    exec /usr/sbin/apache2ctl -D FOREGROUND
fi
