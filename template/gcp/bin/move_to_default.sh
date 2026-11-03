#!/bin/bash

# ----------------------------------------- #
# Turns an export of a named database (my-app, test) into one the local app
# reads, whose data lives in (default). Two throwaway Firestore emulators run
# one after the other (bin/move_db.py does the reading and writing):
#   1. imports the export and reads every document out to a file;
#   2. starts empty, writes them into (default), and saves to OUT_DIR.
# One emulator cannot do both: an emulator that imported a database always
# saves that database again, even after its documents are deleted.
#
# The regular emulator is never touched: the throwaway ones have their own
# ports, project name, and temp folder (the Firebase CLI finds a running
# emulator by project name through files in $TMPDIR, and would otherwise
# reach the regular one).
#
# Usage: ./move_to_default.sh IMPORT_DIR DATABASE OUT_DIR
#   IMPORT_DIR  holds firebase-export-metadata.json and firestore_export/
#   OUT_DIR     receives the converted export (same layout)
# ----------------------------------------- #

set -euo pipefail

USAGE="Usage: move_to_default.sh IMPORT_DIR DATABASE OUT_DIR"
IMPORT_DIR=$(cd "${1:?$USAGE}" && pwd)
DATABASE=${2:?$USAGE}
OUT_DIR=${3:?$USAGE}
GCP_DIR=$(cd "$(dirname "$0")/.." && pwd)
# Any demo- project works: the regular emulator imports data under its own.
PROJECT="demo-sync"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT
cat > "${WORK_DIR}/firebase.json" <<'EOF'
{
  "emulators": {
    "firestore": { "port": 8170, "websocketPort": 9250 },
    "hub": { "port": 4410 },
    "logging": { "port": 4510 },
    "ui": { "enabled": false },
    "singleProjectMode": true
  }
}
EOF

mkdir -p "${OUT_DIR}"
OUT_DIR=$(cd "${OUT_DIR}" && pwd)
DOCS="${WORK_DIR}/docs.pickle"
MOVE="uv run --quiet --project '${GCP_DIR}' python '${GCP_DIR}/bin/move_db.py'"

exec_emulator() {
    (cd "${WORK_DIR}" && TMPDIR="${WORK_DIR}" firebase emulators:exec \
        --project "${PROJECT}" --only firestore "$@")
}

echo "Reading database ${DATABASE} from the export..."
exec_emulator --import "${IMPORT_DIR}" "${MOVE} dump '${DATABASE}' '${DOCS}'"

echo "Writing it into (default)..."
exec_emulator --export-on-exit "${OUT_DIR}" "${MOVE} load '${DOCS}'"

if [ ! -f "${OUT_DIR}/firestore_export/firestore_export.overall_export_metadata" ]; then
    echo "The converted data was not saved." >&2
    exit 1
fi
