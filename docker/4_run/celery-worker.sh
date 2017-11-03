#!/usr/bin/env bash

source /install_scripts.sh
source /manage.sh celery worker -- -C
