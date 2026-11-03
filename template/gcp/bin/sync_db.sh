#!/bin/bash

# ----------------------------------------- #
# Copies a cloud Firestore database into the local emulator's saved data, so
# the next `make emulator` starts with it. Exports the database to a backup
# bucket (created once), downloads the export, and removes it from the bucket.
# The local app reads the emulator's (default) database, so an export of a
# named database (my-app, test) is moved into (default) first
# (bin/move_to_default.sh). The local data is replaced only after every step
# worked. Only Firestore is replaced; the saved emulator accounts and storage
# files are kept. Uploaded files are not copied.
#
# Usage: ./sync_db.sh PROJECT_ID DATABASE [DATA_DIR]
# ----------------------------------------- #

set -euo pipefail

GCP_PROJECT_ID=${1:?"Usage: sync_db.sh PROJECT_ID DATABASE [DATA_DIR]"}
DATABASE=${2:?"Usage: sync_db.sh PROJECT_ID DATABASE [DATA_DIR]"}
FIRESTORE_DATA=${3:-"./firestore_data"}
EXPORT_NAME="firestore_export"
BUCKET_NAME="${GCP_PROJECT_ID}-firestore-backup"
METADATA="${FIRESTORE_DATA}/firebase-export-metadata.json"

# A running emulator saves its memory over the data folder when it stops,
# which would throw this copy away.
if nc -z 127.0.0.1 8070 >/dev/null 2>&1; then
    echo "The Firestore emulator is running. Stop it (Ctrl+C, and wait for the export to finish), then run this again."
    exit 1
fi

printf "Replace the local emulator's Firestore data with database '%s' from %s? [y/N] " "${DATABASE}" "${GCP_PROJECT_ID}"
read -r answer
case "$answer" in [yY]*) ;; *) echo "Nothing changed."; exit 0 ;; esac

if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${BUCKET_NAME}" --project="${GCP_PROJECT_ID}"
    echo "Bucket ${BUCKET_NAME} created."
fi

echo "Exporting database ${DATABASE}..."
gcloud firestore export "gs://${BUCKET_NAME}/${EXPORT_NAME}" \
    --project="${GCP_PROJECT_ID}" --database="${DATABASE}"

echo "Downloading the export..."
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT
mkdir "${TMP_DIR}/cloud"
gcloud storage cp --recursive "gs://${BUCKET_NAME}/${EXPORT_NAME}" "${TMP_DIR}/cloud/"
gcloud storage rm -r "gs://${BUCKET_NAME}/${EXPORT_NAME}"

READY="${TMP_DIR}/cloud"
if [ "${DATABASE}" != "(default)" ]; then
    cat > "${TMP_DIR}/cloud/firebase-export-metadata.json" <<META
{"version": "0", "firestore": {"version": "0", "path": "${EXPORT_NAME}",
 "metadata_file": "${EXPORT_NAME}/${EXPORT_NAME}.overall_export_metadata"}}
META
    echo "Moving the data into the emulator's (default) database..."
    "$(dirname "$0")/move_to_default.sh" "${TMP_DIR}/cloud" "${DATABASE}" "${TMP_DIR}/local"
    READY="${TMP_DIR}/local"
fi

mkdir -p "${FIRESTORE_DATA}"
rm -rf "${FIRESTORE_DATA:?}/${EXPORT_NAME}"
mv "${READY}/${EXPORT_NAME}" "${FIRESTORE_DATA}/${EXPORT_NAME}"

# The emulator imports only what this file lists. Point its Firestore entry at
# the new export and keep the auth and storage entries already there.
python3 - "${METADATA}" "${EXPORT_NAME}" <<'EOF'
import json, os, sys

path, name = sys.argv[1], sys.argv[2]
meta = json.load(open(path)) if os.path.exists(path) else {"version": "0"}
meta["firestore"] = {
    "version": meta.get("firestore", {}).get("version", "0"),
    "path": name,
    "metadata_file": f"{name}/{name}.overall_export_metadata",
}
with open(path, "w") as f:
    json.dump(meta, f, indent=2)
EOF

echo "Done. Start the emulator with: make emulator"
