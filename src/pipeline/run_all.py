#!/usr/bin/env python3
"""
Run the complete Open Targets Cancer MeSH pipeline.

Steps:
1. Extract cancer diseases from Open Targets
2. Extract MeSH C04.588 hierarchy & build crosswalk
3. Add Entrez Gene IDs & produce final 4-column output

Final output: gene_disease_mesh_final.tsv
Columns: disease_mesh_id, gene_entrez_id, ot_score, evidence_count
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import load_config
from src.pipeline import extract_diseases, build_crosswalk, add_entrez


def main():
    """Run the complete pipeline."""
    print("=" * 60)
    print("OPEN TARGETS CANCER MeSH PIPELINE")
    print("=" * 60)

    config = load_config()

    # Step 1: Extract diseases
    print("\n")
    extract_diseases.run(config, verbose=True)

    # Step 2: Build crosswalk (extracts MeSH C04.588 live)
    print("\n")
    build_crosswalk.run(config, verbose=True)

    # Step 3: Add Entrez IDs & produce final output
    print("\n")
    final = add_entrez.run(config, verbose=True)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print("\nFinal output: data/processed/gene_disease_mesh_final.tsv")
    print(f"  {len(final):,} rows")
    print(f"  Columns: disease_mesh_id, gene_entrez_id, ot_score, evidence_count")
    print("\nCrosswalks: data/processed/crosswalks/")
    print("  - disease_mesh_crosswalk.csv")
    print("  - ensembl_entrez.csv")


if __name__ == "__main__":
    main()
