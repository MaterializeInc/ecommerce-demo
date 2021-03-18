#!/bin/bash

set -euo pipefail

wait-for-it --timeout=60 mysql:3306

cd /loadgen

python generate_load.py