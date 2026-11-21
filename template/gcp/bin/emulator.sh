#!/bin/bash

# ----------------------------------------- #
# Runs the Firebase emulators named in firebase.json, with auto import/export
#
# Usage: ./emulator.sh [OPTIONS]
#   --empty     Start with empty database (no import/export)
#   --data DIR  Data directory (default: ./firestore_data)
# ----------------------------------------- #

FIRESTORE_DATA="./firestore_data"
EMPTY_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --empty|-e) EMPTY_MODE=true; shift ;;
        --data|-d)  FIRESTORE_DATA="$2"; shift 2 ;;
        *) echo "Usage: ./emulator.sh [--empty] [--data DIR]"; exit 1 ;;
    esac
done

mkdir -p "${FIRESTORE_DATA}"

# stackkit:begin api
# stackkit:begin jobs
# stackkit:begin database
# Runs the jobs the server starts on this computer (job_service/emulator.py)
JOB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../job_service" && pwd)"
(cd "$JOB_DIR" && exec uv run --package job_service python emulator.py) &
JOBS_EMULATOR=$!
trap 'kill "$JOBS_EMULATOR" 2>/dev/null' EXIT
# stackkit:end database
# stackkit:end jobs
# stackkit:end api

if [ "$EMPTY_MODE" = true ]; then
    echo "Starting emulators (empty mode)..."
    firebase emulators:start

else
    if [ ! -f "${FIRESTORE_DATA}/firebase-export-metadata.json" ]; then
        echo "Warning: No existing data found in ${FIRESTORE_DATA}."
        # stackkit:begin database
        echo "To sync data from remote, run: make -C gcp sync-db"
        # stackkit:end database
        echo ""
    fi

    echo "Starting emulators with import/export..."
    firebase emulators:start \
        --import="${FIRESTORE_DATA}" \
        --export-on-exit
fi
