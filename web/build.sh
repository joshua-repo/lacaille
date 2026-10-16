#!/usr/bin/env bash
# Build the dashboard front end without installing anything on the host.
#
# Node lives only inside a throwaway container: `--rm` means it is gone the
# moment the build ends, and `-u $(id -u)` means the files it writes into
# src/pictor/_web and web/node_modules belong to you rather than to root.
# Deliberately NOT the ib-gateway container -- that one holds a live broker
# session, has a different lifecycle, and would lose anything installed into it
# on its next image update.
#
# The whole repo is mounted, not just web/, because the build writes its output
# into the Python package (src/pictor/_web) so the wheel carries it.
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker run --rm \
  -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/repo" -w /repo/web \
  node:22-alpine sh -c "npm install --no-fund --no-audit && npm run build"
