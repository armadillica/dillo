#!/bin/bash -e

docker build -t armadillica/dillo:latest -f run.docker .

echo "Done, built armadillica/dillo:latest"
