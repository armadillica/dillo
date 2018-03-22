#!/bin/bash -e

DEPLOY_BRANCH=${DEPLOY_BRANCH:-production}

# macOS does not support readlink -f, so we use greadlink instead
if [[ `uname` == 'Darwin' ]]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using brew."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi

ROOT="$(dirname "$(dirname "$($readlink -f "$0")")")"
DEPLOYDIR="$ROOT/docker/4_run/deploy"
PROJECT_NAME="$(basename $ROOT)"

if [ -e $DEPLOYDIR ]; then
    echo "$DEPLOYDIR already exists, press [ENTER] to DESTROY AND DEPLOY, Ctrl+C to abort."
    read dummy
    rm -rf $DEPLOYDIR
else
    echo -n "Deploying to $DEPLOYDIR… "
    echo "press [ENTER] to continue, Ctrl+C to abort."
    read dummy
fi

cd ${ROOT}
mkdir -p $DEPLOYDIR
REMOTE_ROOT="$DEPLOYDIR/$PROJECT_NAME"

if [ -z "$SKIP_BRANCH_CHECK" ]; then
    # Check that we're on production branch.
    if [ $(git rev-parse --abbrev-ref HEAD) != "$DEPLOY_BRANCH" ]; then
        echo "You are NOT on the $DEPLOY_BRANCH branch, refusing to deploy." >&2
        exit 1
    fi

    # Check that production branch has been pushed.
    if [ -n "$(git log origin/$DEPLOY_BRANCH..$DEPLOY_BRANCH --oneline)" ]; then
        echo "WARNING: not all changes to the $DEPLOY_BRANCH branch have been pushed."
        echo "Press [ENTER] to continue deploying current origin/$DEPLOY_BRANCH, CTRL+C to abort."
        read dummy
    fi
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
    echo $MODULE_DIR
}

# Find our modules
echo "==================================================================="
echo "LOCAL MODULE LOCATIONS"
PILLAR_DIR=$(find_module pillar)
SDK_DIR=$(find_module pillarsdk)

echo "Pillar  : $PILLAR_DIR"
echo "SDK     : $SDK_DIR"

if [ -z "$PILLAR_DIR" -o -z "$SDK_DIR" ];
then
    exit 1
fi

function git_clone() {
    PROJECT_NAME="$1"
    BRANCH="$2"
    LOCAL_ROOT="$3"

    echo "==================================================================="
    echo "CLONING REPO ON $PROJECT_NAME @$BRANCH"
    URL=$(git -C $LOCAL_ROOT remote get-url origin)
    git -C $DEPLOYDIR clone --depth 1 --branch $BRANCH $URL $PROJECT_NAME
}

git_clone pillar-python-sdk master $SDK_DIR
git_clone pillar $DEPLOY_BRANCH $PILLAR_DIR
git_clone dillo $DEPLOY_BRANCH $ROOT

# Gulp everywhere
GULP=$ROOT/node_modules/.bin/gulp
if [ ! -e $GULP -o gulpfile.js -nt $GULP ]; then
    npm install
    touch $GULP  # installer doesn't always touch this after a build, so we do.
fi
$GULP --cwd $DEPLOYDIR/pillar --production
$GULP --cwd $DEPLOYDIR/dillo --production

echo
echo "==================================================================="
echo "Deploy of ${PROJECT_NAME} is ready for dockerisation."
echo "==================================================================="
