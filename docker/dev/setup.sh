#!/bin/bash

. /data/venv/bin/activate && python /data/git/dillo/dillo/manage.py db upgrade --directory=/data/git/dillo/dillo/migrations/
. /data/venv/bin/activate && python /data/git/dillo/dillo/manage.py setup
npm install -g gulp
cd /data/git/dillo && npm install
gulp
cd /
