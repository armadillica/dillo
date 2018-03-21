#!/bin/bash -e

# macOS does not support readlink -f, so we use greadlink instead
if [[ `uname` == 'Darwin' ]]; then
    command -v greadlink 2>/dev/null 2>&1 || { echo >&2 "Install greadlink using brew."; exit 1; }
    readlink='greadlink'
else
    readlink='readlink'
fi
ROOT="$(dirname "$(dirname "$($readlink -f "$0")")")"
DOCKERDIR="$ROOT/docker/4_run"

case "$(basename "$0")" in
    build-quick.sh)
        pushd "$ROOT/docker/4_run"
        ./build.sh
        ;;
    build-all.sh)
        pushd "$ROOT/docker"
        ./full_rebuild.sh
        ;;
    *)
        echo "Unknown script $0, aborting" >&2
        exit 1
esac

popd
echo
echo "Press [ENTER] to push the new Docker image."
read dummy
docker push armadillica/dillo:latest
echo
echo "Build is done, ready to update the server."

