#!/usr/bin/env bash
set -e
export PATH="/home/azer/nodejs/bin:$PATH"
cd /home/azer/CodeReviewQA/prototype/dashboard
./node_modules/.bin/ng build --configuration development 2>&1 | tail -20