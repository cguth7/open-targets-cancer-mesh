#!/bin/bash
# Phase 2: Download large Open Targets association files (~5-8GB total)
# - Indirect associations: matches Platform UI (includes inherited from disease hierarchy)
# - Direct associations: only explicit evidence links

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../data/opentargets"

if [ ! -d "${DATA_DIR}/disease" ]; then
    echo "ERROR: Disease index not found. Run ./download_phase1.sh first."
    exit 1
fi

echo "=== Downloading Indirect Associations (Overall) ==="
echo "This is what you see on Open Targets Platform disease pages"
rsync -rpltvz --delete \
    rsync.ebi.ac.uk::pub/databases/opentargets/platform/latest/output/association_by_overall_indirect \
    "${DATA_DIR}/"

echo ""
echo "=== Downloading Direct Associations (Overall) ==="
echo "Only explicit evidence links (stricter, fewer associations)"
rsync -rpltvz --delete \
    rsync.ebi.ac.uk::pub/databases/opentargets/platform/latest/output/association_overall_direct \
    "${DATA_DIR}/"

echo ""
echo "=== Phase 2 Download Complete ==="
echo "Data location: ${DATA_DIR}"
echo ""
echo "Next step: python scripts/build_edge_list.py"
