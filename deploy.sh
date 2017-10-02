#!/bin/bash -e

if [ -z "$1" ]; then
    echo "Usage: $0 {host-to-deploy-to}" >&2
    exit 1
fi

echo -n "Deploying to ${DEPLOYHOST}... "

if ! ping ${DEPLOYHOST} -q -c 1 -W 2 >/dev/null; then
    echo "host ${DEPLOYHOST} cannot be pinged, refusing to deploy." >&2
    exit 2
fi

echo "press [ENTER] to continue, Ctrl+C to abort."
read dummy


# Deploys the current production branch to the production machine.
PROJECT_NAME="dillo"
DOCKER_NAME="dillo"
CELERY_WORKER_DOCKER_NAME="celery_worker"
CELERY_BEAT_DOCKER_NAME="celery_beat"
REMOTE_ROOT="/data/git/${PROJECT_NAME}"

SSH="ssh -o ClearAllForwardings=yes ${DEPLOYHOST}"

# macOS does not support readlink -f, so we use greadlink instead
if [[ `uname` == 'Darwin' ]]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using brew."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi

ROOT="$(dirname "$($readlink -f "$0")")"
cd ${ROOT}

# Check that we're on production branch.
#if [ $(git rev-parse --abbrev-ref HEAD) != "production" ]; then
#    echo "You are NOT on the production branch, refusing to deploy." >&2
#    exit 1
#fi

# Check that production branch has been pushed.
if [ -n "$(git log origin/production..production --oneline)" ]; then
    echo "WARNING: not all changes to the production branch have been pushed."
    echo "Press [ENTER] to continue deploying current origin/production, CTRL+C to abort."
    read dummy
fi

function find_module()
{
    MODULE_NAME=$1
    MODULE_DIR=$(python <<EOT
from __future__ import print_function
import os.path
try:
    import ${MODULE_NAME}
except ImportError:
    raise SystemExit('${MODULE_NAME} not found on Python path. Are you in the correct venv?')

print(os.path.dirname(os.path.dirname(${MODULE_NAME}.__file__)))
EOT
)

    if [ $(git -C $MODULE_DIR rev-parse --abbrev-ref HEAD) != "production" ]; then
        echo "${MODULE_NAME}: ($MODULE_DIR) NOT on the production branch, refusing to deploy." >&2
        exit 1
    fi

    echo $MODULE_DIR
}

# Find our modules
PILLAR_DIR=$(find_module pillar)
DILLO_DIR=$(find_module dillo)

echo "Pillar  : $PILLAR_DIR"
echo "Dillo : $DILLO_DIR"

if [ -z "$PILLAR_DIR" -o -z "$DILLO_DIR" ];
then
    exit 1
fi

# SSH to production to pull all files in
function git_pull() {
    PROJECT_NAME="$1"
    BRANCH="$2"
    REMOTE_ROOT="/data/git/${PROJECT_NAME}"

    echo "==================================================================="
    echo "UPDATING FILES ON ${PROJECT_NAME}"
    ${SSH} git -C ${REMOTE_ROOT} fetch origin ${BRANCH}
    ${SSH} git -C ${REMOTE_ROOT} log origin/${BRANCH}..${BRANCH} --oneline
    ${SSH} git -C ${REMOTE_ROOT} merge --ff-only origin/${BRANCH}
}

git_pull pillar-python-sdk master
git_pull pillar production
git_pull dillo production

# Update the virtualenv
#${SSH} -t docker exec ${DOCKER_NAME} /data/venv/bin/pip install -U -r ${REMOTE_ROOT}/requirements.txt --exists-action w

# RSync the world
./rsync_ui.sh ${DEPLOYHOST}

# Notify Bugsnag of this new deploy.
echo
echo "==================================================================="
GIT_REVISION=$(${SSH} git -C ${REMOTE_ROOT} describe --always)
echo "Notifying Bugsnag of this new deploy of revision ${GIT_REVISION}."
BUGSNAG_API_KEY=$(${SSH} python -c "\"import sys; sys.path.append('${REMOTE_ROOT}'); import config_local; print(config_local.BUGSNAG_API_KEY)\"")
curl --data "apiKey=${BUGSNAG_API_KEY}&revision=${GIT_REVISION}" https://notify.bugsnag.com/deploy
echo

# Wait for [ENTER] to restart the server
echo
echo "==================================================================="
echo "NOTE: If you want to edit config_local.py on the server, do so now."
echo "NOTE: Press [ENTER] to continue and restart the server process."
read dummy
echo "Gracefully restarting server process"
${SSH} docker exec ${DOCKER_NAME} apache2ctl graceful
echo "Server process restarted"

echo
echo "==================================================================="
echo "Restarting Celery worker."
${SSH} docker restart ${CELERY_WORKER_DOCKER_NAME}
echo "Celery worker docker restarted"
echo "Restarting Celery beat."
${SSH} docker restart ${CELERY_BEAT_DOCKER_NAME}
echo "Celery beat docker restarted"


echo
echo "==================================================================="
echo "Clearing front page from Redis cache."
${SSH} docker exec redis redis-cli DEL pwview//

echo
echo "==================================================================="
echo "Deploy of ${PROJECT_NAME} is done."
echo "==================================================================="
