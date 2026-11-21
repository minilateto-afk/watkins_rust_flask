#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
printf 'Project directory: %s\n' "$PWD"
printf 'Release: %s\n' "$(cat RELEASE_ID.txt)"
python verify_release.py
# Docker build reprocesses the workbook and runs all Flask route tests.
docker compose up -d --build
printf '\nBuild complete. Open the forwarded Codespaces port 5050.\n'
docker compose ps
