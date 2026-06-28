#!/usr/bin/env bash
set -euo pipefail

APP_NAME="pm-app"

docker rm -f "$APP_NAME" >/dev/null 2>&1 || true
