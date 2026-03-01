#!/bin/bash
# Wrapper to load .env before running a command (for launchd/cron)
cd "$(dirname "$0")/.."
[ -f .env ] && export $(grep -v '^#' .env | xargs)
exec "$@"
