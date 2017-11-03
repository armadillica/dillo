#!/usr/bin/env bash

set -e

# macOS does not support readlink -f, so we use greadlink instead
if [ $(uname) == 'Darwin' ]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using 'brew install coreutils'."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi

TOPDEVDIR="$($readlink -f ../../..)"
echo "Top-level development dir is $TOPDEVDIR"

WHEELHOUSE="$($readlink -f ../4_run/wheelhouse)"
if [ -z "$WHEELHOUSE" ]; then
    echo "Error, ../4_run might not exist." >&2
    exit 2
fi

echo "Wheelhouse is $WHEELHOUSE"
mkdir -p "$WHEELHOUSE"

docker build -t pillar_wheelbuilder -f build.docker .

GID=$(id -g)
docker run --rm -i \
    -v "$WHEELHOUSE:/data/wheelhouse" \
    -v "$TOPDEVDIR:/data/topdev" \
    pillar_wheelbuilder <<EOT
set -e
# Build wheels for all dependencies.
cd /data/topdev/dillo
pip3 install wheel
pip3 wheel --wheel-dir=/data/wheelhouse -r requirements.txt
chown -R $UID:$GID /data/wheelhouse

# Install the dependencies so that we can get a full freeze.
pip3 install --no-index --find-links=/data/wheelhouse -r requirements.txt
pip3 freeze | grep -v '^-[ef] ' > /data/wheelhouse/requirements.txt
EOT

# Remove our own projects, they shouldn't be installed as wheel (for now).
rm -f $WHEELHOUSE/{dillo,pillar,pillarsdk}*.whl
