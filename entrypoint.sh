#!/bin/sh
set -e

# Ensure volume directories exist
mkdir -p /data/text-fabric-data /data/quizzes

# Copy pre-downloaded TF data to the volume if not already there
if [ ! -d "/data/text-fabric-data/github/ETCBC/bhsa/tf" ]; then
    echo "Copying pre-downloaded Text-Fabric data to volume..."
    cp -r /root/text-fabric-data/* /data/text-fabric-data/
    echo "Done."
fi

exec tf-api
