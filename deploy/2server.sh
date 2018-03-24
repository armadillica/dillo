#!/bin/bash -e

# macOS does not support readlink -f, so we use greadlink instead
if [[ `uname` == 'Darwin' ]]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using brew."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi
ROOT="$(dirname "$(dirname "$($readlink -f "$0")")")"
PROJECT_NAME="$(basename $ROOT)"
DOCKER_DEPLOYDIR="$ROOT/docker/4_run/deploy"
DOCKER_IMAGE="armadillica/dillo:latest"
REMOTE_SECRET_CONFIG_DIR="/data/config"
REMOTE_DOCKER_COMPOSE_DIR="/root/docker"

#################################################################################
case $1 in
    cloud*)
        DEPLOYHOST="$1"
        ;;
    *)
        echo "Use $0 hostname" >&2
        exit 1
esac
SSH_OPTS="-o ClearAllForwardings=yes -o PermitLocalCommand=no"
SSH="ssh $SSH_OPTS $DEPLOYHOST"
SCP="scp $SSH_OPTS"

echo -n "Deploying to $DEPLOYHOST… "

if ! ping $DEPLOYHOST -q -c 1 -W 2 >/dev/null; then
    echo "host $DEPLOYHOST cannot be pinged, refusing to deploy." >&2
    exit 2
fi

cat <<EOT
[ping OK]

Make sure that you have pushed the $DOCKER_IMAGE
docker image to Docker Hub.

press [ENTER] to continue, Ctrl+C to abort.
EOT
read dummy

#################################################################################
echo "==================================================================="
echo "Bringing remote Docker up to date…"
$SSH mkdir -p $REMOTE_DOCKER_COMPOSE_DIR
$SCP \
    $ROOT/docker/{docker-compose.yml,renew-letsencrypt.sh,mongo-backup.{cron,sh}} \
    $DEPLOYHOST:$REMOTE_DOCKER_COMPOSE_DIR
$SSH -T <<EOT
set -e
cd $REMOTE_DOCKER_COMPOSE_DIR
docker pull $DOCKER_IMAGE
docker-compose up -d
EOT

# Notify Sentry of this new deploy.
# and https://docs.sentry.io/api/releases/post-organization-releases/
# and https://sentry.io/api/
echo
echo "==================================================================="
REVISION=$(date +'%Y%m%d.%H%M%S.%Z')
echo "Notifying Sentry of this new deploy of revision $REVISION."
SENTRY_RELEASE_URL="$($SSH env PYTHONPATH="$REMOTE_SECRET_CONFIG_DIR" python3 -c "\"import config_secrets; print(config_secrets.SENTRY_RELEASE_URL)\"")"
curl -s "$SENTRY_RELEASE_URL" -XPOST -H 'Content-Type: application/json' -d "{\"version\": \"$REVISION\"}" | json_pp
echo

echo
echo "==================================================================="
echo "Deploy to $DEPLOYHOST done."
echo "==================================================================="
