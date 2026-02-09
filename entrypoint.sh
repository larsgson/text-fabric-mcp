#!/bin/sh
set -e

MARKER="/data/text-fabric-data/.runtime-compiled"

# Ensure volume directories exist
mkdir -p /data/text-fabric-data /data/quizzes

# Copy pre-downloaded TF data to the volume if not already there.
if [ ! -d "/data/text-fabric-data/github/ETCBC/bhsa/tf" ]; then
    echo "Copying pre-downloaded Text-Fabric data to volume..."
    cp -r /root/text-fabric-data/* /data/text-fabric-data/
    echo "Done."
fi

# Remove pre-compiled binary caches that were built during Docker build
# (HOME=/root). The pickled .tfx files contain environment-specific state
# and must be recompiled at runtime (HOME=/data). A marker file tracks
# whether the cache was already rebuilt in the runtime environment.
if [ ! -f "$MARKER" ]; then
    echo "Clearing build-time TF caches for runtime recompilation..."
    find /data/text-fabric-data -type d -name ".tf" -exec rm -rf {} + 2>/dev/null || true
    touch "$MARKER"
    echo "TF will recompile binary caches on first load (~30-60s)."
fi

exec tf-api
