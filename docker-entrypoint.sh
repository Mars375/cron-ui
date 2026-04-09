#!/bin/sh
set -eu

DB_PATH="${CRON_UI_DB_PATH:-/app/data/cron-ui.sqlite3}"
DB_DIR=$(dirname "$DB_PATH")

mkdir -p "$DB_DIR"
chown -R app:app "$DB_DIR"

exec gosu app "$@"
