#!/bin/bash

# ----------------------------------------- #
# This script exports the firestore data
# to a bucket and downloads it
# to a local directory.
# ----------------------------------------- #

# Check if the bucket exists
GCP_PROJECT_ID=${1:-"<TODO>"}
FIRESTORE_DATA=${2:-"./firestore_data"}
EXPORT_NAME=${3:-"firestore_export"}
BUCKET_NAME="${GCP_PROJECT_ID}-firestore-backup"

# Creates backup buckets if needed.
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
    # Create the bucket if it does not exist
    gcloud storage buckets create "gs://${BUCKET_NAME}" --project="${GCP_PROJECT_ID}"
    echo "Bucket $BUCKET_NAME created."
else
    echo "Bucket $BUCKET_NAME already exists."
fi

echo "Exporting the staging firestore data...";
gcloud firestore export "gs://${BUCKET_NAME}/${EXPORT_NAME}" --project="${GCP_PROJECT_ID}";

# Moves the exported data to a working directory
echo "Downloading dump...";
gcloud storage cp --recursive "gs://${BUCKET_NAME}/${EXPORT_NAME}" ./
[ -d "${FIRESTORE_DATA}" ] && rm -r "${FIRESTORE_DATA}";
mkdir "${FIRESTORE_DATA}";
mv "${EXPORT_NAME}" "${FIRESTORE_DATA}";

# Cleanup
gcloud storage rm -r "gs://${BUCKET_NAME}/${EXPORT_NAME}";
