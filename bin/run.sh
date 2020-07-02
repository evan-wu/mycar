#!/bin/bash
SHELL_FOLDER=$(cd "$(dirname "$0")";pwd)

export PYTHON_PATH=$SHELL_FOLDER/../src
python3 src/car.py $1 $2
