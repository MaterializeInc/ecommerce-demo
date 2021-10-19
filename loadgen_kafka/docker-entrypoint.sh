#!/bin/bash

set -euo pipefail

wait-for-it --timeout=60 mysql:3306
wait-for-it --timeout=60 debezium:8083
wait-for-it --timeout=60 zookeeper:2181
wait-for-it --timeout=60 kafka:9092


cd /loadgen

python generate_load.py