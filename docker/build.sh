#!/usr/bin/env bash

set -xe

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR/3_buildwheels
bash build.sh

cd $DIR/4_run
bash build.sh
