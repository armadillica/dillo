#!/usr/bin/env bash

source /install_scripts.sh
source /manage.sh celery beat -- \
    --schedule /data/storage/pillar/celerybeat-schedule.db \
    --pid /data/storage/pillar/celerybeat.pid
