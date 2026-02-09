#!/bin/sh
set -e

MARKER="/data/text-fabric-data/.cache-ok"

# Ensure volume directories exist
mkdir -p /data/text-fabric-data /data/quizzes

# On first run (or after a new Docker image), wipe stale data from the
# volume and copy the known-good pre-downloaded data from the image.
# Remove compiled caches so TF recompiles them at runtime.
if [ ! -f "$MARKER" ]; then
    echo "Provisioning Text-Fabric data from Docker image..."
    rm -rf /data/text-fabric-data/github
    cp -r /root/text-fabric-data/* /data/text-fabric-data/
    echo "Removing build-time compiled caches..."
    find /data/text-fabric-data -type d -name ".tf" -exec rm -rf {} + 2>/dev/null || true
    # Diagnostic: show what we have
    echo "=== TF data on volume ==="
    find /data/text-fabric-data -maxdepth 5 -type f | head -30
    echo "=== end ==="
    touch "$MARKER"
    echo "TF will recompile binary caches on first load (~30-60s)."
fi

exec tf-api
