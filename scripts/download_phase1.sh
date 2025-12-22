#!/bin/bash
# Phase 1: Download small Open Targets indexes (~200MB total)
# - Disease index: disease definitions, therapeutic areas, MeSH crossrefs
# - Target index: gene IDs and symbols

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../data/opentargets"

echo "Creating data directory..."
mkdir -p "${DATA_DIR}"

echo ""
echo "=== Downloading Disease Index ==="
echo "Source: Open Targets Platform (latest release)"
rsync -rpltvz --delete \
    rsync.ebi.ac.uk::pub/databases/opentargets/platform/latest/output/disease \
    "${DATA_DIR}/"

echo ""
echo "=== Downloading Target Index ==="
rsync -rpltvz --delete \
    rsync.ebi.ac.uk::pub/databases/opentargets/platform/latest/output/target \
    "${DATA_DIR}/"

echo ""
echo "=== Phase 1 Download Complete ==="
echo "Data location: ${DATA_DIR}"
echo ""
echo "Next steps:"
echo "  1. Run: python scripts/explore_data.py"
echo "  2. When ready for full edge list: ./download_phase2.sh"
