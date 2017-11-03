#!/usr/bin/env bash

set -e
cd /data/git/dillo
exec python manage.py "$@"
