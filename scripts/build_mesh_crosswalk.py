#!/usr/bin/env python3
"""
Build cancer gene-disease associations with MeSH crosswalk.

This script:
1. Loads cancer diseases from Phase 1 (OT dbXRefs → MeSH)
2. Loads association_overall_direct (gene-disease scores)
3. Joins with MeSH C04 hierarchy for tree numbers/levels
4. Outputs final dataset with granularity control

MeSH Source: Open Targets dbXRefs ONLY (no external crosswalks)
"""

import pandas as pd
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MESH_DIR = DATA_DIR / "mesh"
OT_DIR = DATA_DIR / "opentargets"


def load_cancer_diseases() -> pd.DataFrame:
    """Load cancer diseases with MeSH from Phase 1."""
    path = PROCESSED_DIR / "cancer_diseases_mesh_crosswalk.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Run explore_data.py first: {path}")
    return pd.read_parquet(path)


def load_associations() -> pd.DataFrame:
    """Load association_overall_direct parquet files."""
    assoc_dir = OT_DIR / "association_overall_direct"
    if not assoc_dir.exists():
        raise FileNotFoundError(f"Download associations first: {assoc_dir}")

    files = list(assoc_dir.glob("*.parquet"))
    print(f"  Loading {len(files)} parquet files...")
    return pd.concat([pd.read_parquet(f) for f in files])


def load_mesh_c04() -> pd.DataFrame:
    """Load MeSH C04 (neoplasms) hierarchy."""
    path = MESH_DIR / "mesh_c04_complete.csv"
    if not path.exists():
        raise FileNotFoundError(f"MeSH C04 not found: {path}")
    return pd.read_csv(path)


def build_crosswalk(cancer_diseases: pd.DataFrame, mesh_c04: pd.DataFrame) -> pd.DataFrame:
    """
    Build disease → MeSH crosswalk with hierarchy info.

    Source: OT dbXRefs only (no external crosswalks).
    """
    # Explode meshIds (one row per disease-mesh pair)
    with_mesh = cancer_diseases[cancer_diseases['meshIds'].notna()].copy()

    rows = []
    for _, row in with_mesh.iterrows():
        for mesh_id in row['meshIds']:
            rows.append({
                'diseaseId': row['diseaseId'],
                'diseaseName': row['diseaseName'],
                'meshId': mesh_id
            })

    crosswalk = pd.DataFrame(rows)
    print(f"  Exploded to {len(crosswalk)} disease-mesh pairs")

    # Join with MeSH C04 for tree numbers and levels
    crosswalk = crosswalk.merge(
        mesh_c04.rename(columns={'mesh_id': 'meshId', 'mesh_name': 'mesh_name'}),
        on='meshId',
        how='left'
    )

    # Summary
    in_c04 = crosswalk['tree_number'].notna().sum()
    print(f"  {in_c04} pairs have C04 tree numbers ({in_c04/len(crosswalk)*100:.1f}%)")

    return crosswalk


def build_final_dataset(
    associations: pd.DataFrame,
    cancer_diseases: pd.DataFrame,
    crosswalk: pd.DataFrame
) -> pd.DataFrame:
    """
    Build final gene-disease-mesh dataset.
    """
    # Filter associations to cancer diseases
    cancer_ids = set(cancer_diseases['diseaseId'])
    cancer_assoc = associations[associations['diseaseId'].isin(cancer_ids)].copy()
    print(f"  Filtered to {len(cancer_assoc):,} cancer associations")

    # Join with crosswalk
    final = cancer_assoc.merge(
        crosswalk[['diseaseId', 'diseaseName', 'meshId', 'mesh_name', 'tree_number', 'level']],
        on='diseaseId',
        how='left'
    )

    return final


def create_summaries(final: pd.DataFrame) -> None:
    """Create summary files for analysis."""
    mesh_only = final[final['tree_number'].notna()]

    # Summary by level
    level_summary = mesh_only.groupby('level').agg({
        'targetId': 'nunique',
        'diseaseId': 'nunique',
        'meshId': 'nunique',
        'score': ['count', 'mean', 'median']
    }).round(4)
    level_summary.columns = ['genes', 'diseases', 'mesh_terms', 'associations', 'mean_score', 'median_score']
    level_summary.to_csv(PROCESSED_DIR / 'summary_by_mesh_level.csv')

    # Summary by MeSH term
    mesh_summary = mesh_only.groupby(['meshId', 'mesh_name', 'level']).agg({
        'targetId': 'nunique',
        'diseaseId': 'nunique',
        'score': ['count', 'mean', 'max']
    }).round(4)
    mesh_summary.columns = ['genes', 'diseases', 'associations', 'mean_score', 'max_score']
    mesh_summary = mesh_summary.reset_index().sort_values('associations', ascending=False)
    mesh_summary.to_csv(PROCESSED_DIR / 'mesh_term_summary.csv', index=False)

    # Level 4-5 summary
    level_4_5 = mesh_summary[(mesh_summary['level'] >= 4) & (mesh_summary['level'] <= 5)]
    level_4_5.to_csv(PROCESSED_DIR / 'mesh_level_4_5_summary.csv', index=False)


def create_site_only(crosswalk: pd.DataFrame, final: pd.DataFrame) -> None:
    """
    Create site-only versions (C04.588 hierarchy only, not histologic type).

    Deduplication:
    1. One row per (disease, meshId) in crosswalk, keeping lowest level (most specific)
    2. Aggregate gene associations by (gene, meshId): MAX score, SUM evidenceCount
       This collapses multiple OT diseases that map to the same MeSH term.

    NOTE: For non-site (full) data, multiple tree_numbers per meshId are preserved
    since the same MeSH concept can appear in different hierarchies (polyhierarchy).
    If you need deduped full data, apply similar logic there.
    """
    # Filter crosswalk to site-based MeSH only
    site_crosswalk = crosswalk[
        crosswalk['tree_number'].str.startswith('C04.588', na=False)
    ].copy()

    # Dedupe crosswalk: one row per (disease, meshId), keep lowest level (most specific)
    site_crosswalk = site_crosswalk.sort_values('level', ascending=False)  # highest first
    site_crosswalk = site_crosswalk.drop_duplicates(
        subset=['diseaseId', 'meshId'],
        keep='last'  # keeps lowest level after sort
    ).sort_values(['diseaseId', 'level'])

    site_crosswalk.to_csv(PROCESSED_DIR / 'cancer_mesh_crosswalk_site_only.csv', index=False)

    # Join associations with crosswalk
    final_base = final[['diseaseId', 'targetId', 'score', 'evidenceCount']].drop_duplicates()
    site_joined = final_base.merge(
        site_crosswalk[['diseaseId', 'meshId', 'mesh_name', 'tree_number', 'level']],
        on='diseaseId',
        how='inner'
    )

    # Aggregate by (gene, meshId): MAX score, SUM evidenceCount
    # This collapses multiple OT diseases → same MeSH into one row per gene-mesh pair
    site_final = site_joined.groupby(['targetId', 'meshId']).agg({
        'score': 'max',
        'evidenceCount': 'sum',
        'mesh_name': 'first',
        'tree_number': 'first',
        'level': 'first'
    }).reset_index()

    # Reorder columns
    site_final = site_final[['targetId', 'meshId', 'mesh_name', 'tree_number', 'level', 'score', 'evidenceCount']]

    site_final.to_parquet(PROCESSED_DIR / 'cancer_gene_disease_mesh_site_only.parquet', index=False)
    site_final.to_csv(PROCESSED_DIR / 'cancer_gene_disease_mesh_site_only.csv', index=False)

    print(f"  Site-only crosswalk: {len(site_crosswalk)} rows, {site_crosswalk['diseaseId'].nunique()} diseases, {site_crosswalk['meshId'].nunique()} MeSH terms")
    print(f"  Site-only final: {len(site_final):,} rows (gene-mesh pairs, aggregated)")


def main():
    print("=" * 60)
    print("BUILDING CANCER GENE-DISEASE-MESH DATASET")
    print("=" * 60)
    print("\nMeSH Source: Open Targets dbXRefs ONLY")

    PROCESSED_DIR.mkdir(exist_ok=True)

    # Load data
    print("\n1. Loading cancer diseases...")
    cancer_diseases = load_cancer_diseases()
    print(f"  {len(cancer_diseases):,} diseases, {cancer_diseases['meshIds'].notna().sum()} with MeSH")

    print("\n2. Loading MeSH C04 hierarchy...")
    mesh_c04 = load_mesh_c04()
    print(f"  {len(mesh_c04)} tree paths, {mesh_c04['mesh_id'].nunique()} unique terms")

    print("\n3. Building crosswalk...")
    crosswalk = build_crosswalk(cancer_diseases, mesh_c04)
    crosswalk.to_csv(PROCESSED_DIR / 'cancer_mesh_crosswalk.csv', index=False)
    print(f"  Saved: cancer_mesh_crosswalk.csv")

    print("\n4. Loading associations...")
    associations = load_associations()
    print(f"  {len(associations):,} total associations")

    print("\n5. Building final dataset...")
    final = build_final_dataset(associations, cancer_diseases, crosswalk)

    # Save
    final.to_parquet(PROCESSED_DIR / 'cancer_gene_disease_mesh.parquet', index=False)
    final.to_csv(PROCESSED_DIR / 'cancer_gene_disease_mesh.csv', index=False)
    print(f"  Saved: cancer_gene_disease_mesh.parquet ({len(final):,} rows)")

    print("\n6. Creating summaries...")
    create_summaries(final)
    print("  Saved: summary_by_mesh_level.csv, mesh_term_summary.csv, mesh_level_4_5_summary.csv")

    print("\n7. Creating site-only versions (C04.588)...")
    create_site_only(crosswalk, final)

    # Final stats
    print("\n" + "=" * 60)
    print("FINAL DATASET SUMMARY")
    print("=" * 60)
    print(f"Total rows: {len(final):,}")
    print(f"Unique genes: {final['targetId'].nunique():,}")
    print(f"Unique diseases: {final['diseaseId'].nunique():,}")
    print(f"With MeSH (any): {final['meshId'].notna().sum():,} ({final['meshId'].notna().mean()*100:.1f}%)")
    print(f"With C04 tree: {final['tree_number'].notna().sum():,} ({final['tree_number'].notna().mean()*100:.1f}%)")


if __name__ == "__main__":
    main()
