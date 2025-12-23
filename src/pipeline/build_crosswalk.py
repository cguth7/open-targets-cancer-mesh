#!/usr/bin/env python3
"""
Pipeline Step 2: Build cancer gene-disease-MeSH crosswalk.

This module:
1. Loads cancer diseases from Step 1
2. Extracts MeSH C04.588 hierarchy live from d2025.bin
3. Loads gene-disease associations
4. Joins with MeSH hierarchy
5. Creates final 4-column output for patent matching
"""

import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import load_config, ensure_dir
from src.pipeline.extract_mesh import run as extract_mesh_hierarchy


def load_cancer_diseases(config: dict) -> pd.DataFrame:
    """Load cancer diseases from Step 1 output."""
    path = Path(config["paths"]["processed_dir"]) / "cancer_diseases_mesh_crosswalk.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Run Step 1 first: {path}")
    return pd.read_parquet(path)


def load_associations(config: dict) -> pd.DataFrame:
    """Load gene-disease associations from Open Targets."""
    assoc_dir = Path(config["paths"]["opentargets_dir"]) / "association_overall_direct"
    if not assoc_dir.exists():
        raise FileNotFoundError(
            f"Associations not found: {assoc_dir}. "
            "Run: make download-phase2"
        )

    files = list(assoc_dir.glob("*.parquet"))
    print(f"    Loading {len(files)} parquet files...")
    return pd.concat([pd.read_parquet(f) for f in files])


def build_disease_mesh_crosswalk(
    cancer_diseases: pd.DataFrame,
    mesh_hierarchy: pd.DataFrame
) -> pd.DataFrame:
    """
    Build disease → MeSH crosswalk with hierarchy info.

    Explodes the meshIds list and joins with MeSH tree structure.
    """
    with_mesh = cancer_diseases[cancer_diseases["meshIds"].notna()].copy()

    rows = []
    for _, row in with_mesh.iterrows():
        for mesh_id in row["meshIds"]:
            rows.append({
                "diseaseId": row["diseaseId"],
                "diseaseName": row["diseaseName"],
                "meshId": mesh_id
            })

    crosswalk = pd.DataFrame(rows)

    # Join with MeSH hierarchy for tree numbers and levels
    crosswalk = crosswalk.merge(
        mesh_hierarchy.rename(columns={"mesh_id": "meshId"}),
        on="meshId",
        how="inner"  # Only keep diseases that match C04.588 hierarchy
    )

    # Dedupe: one row per (disease, meshId), keep lowest level (most specific)
    crosswalk = crosswalk.sort_values('level', ascending=False)
    crosswalk = crosswalk.drop_duplicates(
        subset=['diseaseId', 'meshId'],
        keep='last'
    ).sort_values(['diseaseId', 'level'])

    return crosswalk


def build_final_dataset(
    associations: pd.DataFrame,
    cancer_diseases: pd.DataFrame,
    crosswalk: pd.DataFrame
) -> pd.DataFrame:
    """
    Build final gene-mesh dataset aggregated by (gene, mesh).

    Returns 4-column output:
    - meshId (disease)
    - targetId (gene - Ensembl)
    - score (max across diseases)
    - evidenceCount (sum across diseases)
    """
    # Filter associations to cancer diseases with MeSH
    disease_ids = set(crosswalk["diseaseId"])
    cancer_assoc = associations[associations["diseaseId"].isin(disease_ids)].copy()

    # Join with crosswalk
    joined = cancer_assoc.merge(
        crosswalk[["diseaseId", "meshId"]],
        on="diseaseId",
        how="inner"
    )

    # Aggregate by (gene, meshId): MAX score, SUM evidenceCount
    final = joined.groupby(["targetId", "meshId"]).agg({
        "score": "max",
        "evidenceCount": "sum"
    }).reset_index()

    return final


def run(config: dict | None = None, verbose: bool = True) -> dict:
    """
    Run the crosswalk building pipeline step.

    Args:
        config: Configuration dict (loads from file if None)
        verbose: Print progress messages

    Returns:
        Dict with output dataframes
    """
    if config is None:
        config = load_config()

    processed_dir = ensure_dir(Path(config["paths"]["processed_dir"]))
    crosswalks_dir = ensure_dir(processed_dir / "crosswalks")

    if verbose:
        print("Step 2: Building gene-disease-MeSH crosswalk")
        print("-" * 40)

    # Load cancer diseases
    if verbose:
        print("  Loading cancer diseases...")
    cancer_diseases = load_cancer_diseases(config)
    if verbose:
        print(f"    {len(cancer_diseases):,} diseases")

    # Extract MeSH hierarchy LIVE from d2025.bin
    if verbose:
        print("  Extracting MeSH C04.588 hierarchy...")
    mesh_hierarchy = extract_mesh_hierarchy(config, prefix="C04.588", verbose=False)
    if verbose:
        print(f"    {len(mesh_hierarchy)} tree paths, {mesh_hierarchy['mesh_id'].nunique()} terms")

    # Load associations
    if verbose:
        print("  Loading associations...")
    associations = load_associations(config)
    if verbose:
        print(f"    {len(associations):,} associations")

    # Build crosswalk
    if verbose:
        print("  Building disease → MeSH crosswalk...")
    crosswalk = build_disease_mesh_crosswalk(cancer_diseases, mesh_hierarchy)
    crosswalk.to_csv(crosswalks_dir / "disease_mesh_crosswalk.csv", index=False)
    if verbose:
        print(f"    {len(crosswalk)} disease-mesh pairs")
        print(f"    {crosswalk['diseaseId'].nunique()} diseases, {crosswalk['meshId'].nunique()} MeSH terms")

    # Build final aggregated dataset
    if verbose:
        print("  Building gene-mesh dataset...")
    final = build_final_dataset(associations, cancer_diseases, crosswalk)
    if verbose:
        print(f"    {len(final):,} gene-mesh pairs")

    # Save intermediate (before Entrez)
    final.to_parquet(processed_dir / "intermediate" / "gene_mesh_pre_entrez.parquet", index=False)

    if verbose:
        print("  Done!")

    return {
        "crosswalk": crosswalk,
        "final": final,
        "mesh_hierarchy": mesh_hierarchy
    }


def main():
    """CLI entry point."""
    config = load_config()
    run(config, verbose=True)


if __name__ == "__main__":
    main()
