#!/usr/bin/env python3
"""
Phase 2: Build cancer target-disease edge lists with MeSH crosswalk.

This script:
1. Loads the cancer disease list from Phase 1
2. Loads association data (indirect and direct)
3. Filters associations to cancer diseases
4. Joins with target index for gene symbols
5. Outputs edge lists in Parquet and CSV formats

Run after: ./download_phase2.sh
"""

import polars as pl
from pathlib import Path
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"


def check_prerequisites() -> None:
    """Check that Phase 1 and Phase 2 data exist."""
    crosswalk_path = OUTPUT_DIR / "cancer_diseases_mesh_crosswalk.parquet"
    if not crosswalk_path.exists():
        print(f"ERROR: Cancer disease crosswalk not found at {crosswalk_path}")
        print("Run python explore_data.py first (Phase 1).")
        sys.exit(1)

    indirect_path = DATA_DIR / "association_by_overall_indirect"
    direct_path = DATA_DIR / "association_overall_direct"

    if not indirect_path.exists() and not direct_path.exists():
        print("ERROR: Association data not found.")
        print("Run ./download_phase2.sh first.")
        sys.exit(1)


def load_cancer_diseases() -> pl.DataFrame:
    """Load the cancer disease crosswalk from Phase 1."""
    return pl.read_parquet(OUTPUT_DIR / "cancer_diseases_mesh_crosswalk.parquet")


def load_targets() -> pl.LazyFrame:
    """Load the target index for gene symbols."""
    target_path = DATA_DIR / "target"
    if not target_path.exists():
        raise FileNotFoundError(f"Target data not found at {target_path}")
    return pl.scan_parquet(str(target_path / "**" / "*.parquet"))


def load_associations(assoc_type: str) -> pl.LazyFrame:
    """
    Load association data.

    Args:
        assoc_type: Either "indirect" or "direct"
    """
    if assoc_type == "indirect":
        path = DATA_DIR / "association_by_overall_indirect"
    elif assoc_type == "direct":
        path = DATA_DIR / "association_overall_direct"
    else:
        raise ValueError(f"Unknown association type: {assoc_type}")

    if not path.exists():
        raise FileNotFoundError(f"Association data not found at {path}")

    return pl.scan_parquet(str(path / "**" / "*.parquet"))


def build_edge_list(
    cancer_diseases: pl.DataFrame,
    targets: pl.LazyFrame,
    associations: pl.LazyFrame,
    assoc_type: str,
) -> pl.DataFrame:
    """
    Build the edge list by joining associations with cancer diseases and targets.

    Returns a DataFrame with columns:
    - diseaseId: EFO/MONDO ID
    - diseaseName: human-readable name
    - targetId: Ensembl gene ID
    - approvedSymbol: HGNC gene symbol
    - score: overall association score (0-1)
    - meshIds: list of MeSH descriptor IDs (may be null)
    """
    print(f"  Building {assoc_type} edge list...")

    # Get cancer disease IDs for filtering
    cancer_disease_ids = cancer_diseases.select("diseaseId")

    # Get target symbols
    targets_small = targets.select([
        pl.col("id").alias("targetId"),
        pl.col("approvedSymbol"),
    ])

    # Filter associations to cancer diseases and join
    edges = (
        associations
        .select(["diseaseId", "targetId", "score"])
        # Inner join to filter to cancer diseases only
        .join(
            cancer_disease_ids.lazy(),
            on="diseaseId",
            how="inner"
        )
        # Add disease names and MeSH IDs
        .join(
            cancer_diseases.select(["diseaseId", "diseaseName", "meshId"]).lazy(),
            on="diseaseId",
            how="left"
        )
        # Add gene symbols
        .join(
            targets_small,
            on="targetId",
            how="left"
        )
        # Reorder columns
        .select([
            "diseaseId",
            "diseaseName",
            "targetId",
            "approvedSymbol",
            "score",
            pl.col("meshId").alias("meshIds"),
        ])
    )

    # Collect with streaming for memory efficiency
    print(f"  Collecting {assoc_type} associations (streaming)...")
    result = edges.collect(streaming=True)

    return result


def save_edge_list(df: pl.DataFrame, assoc_type: str) -> None:
    """Save edge list to Parquet and CSV."""
    base_name = f"cancer_associations_{assoc_type}"

    # Parquet (keeps list type for meshIds)
    parquet_path = OUTPUT_DIR / f"{base_name}.parquet"
    df.write_parquet(parquet_path)
    print(f"  Saved: {parquet_path}")

    # CSV (convert list to comma-separated string)
    csv_path = OUTPUT_DIR / f"{base_name}.csv"
    csv_df = df.with_columns(
        pl.when(pl.col("meshIds").is_not_null())
        .then(pl.col("meshIds").list.join(","))
        .otherwise(pl.lit(""))
        .alias("meshIds")
    )
    csv_df.write_csv(csv_path)
    print(f"  Saved: {csv_path}")


def print_summary(df: pl.DataFrame, assoc_type: str) -> None:
    """Print summary statistics for the edge list."""
    total_edges = len(df)
    unique_diseases = df.select("diseaseId").n_unique()
    unique_targets = df.select("targetId").n_unique()

    # Score distribution
    score_stats = df.select([
        pl.col("score").min().alias("min"),
        pl.col("score").mean().alias("mean"),
        pl.col("score").median().alias("median"),
        pl.col("score").max().alias("max"),
    ]).row(0, named=True)

    print(f"\n  {assoc_type.upper()} ASSOCIATIONS:")
    print(f"    Total edges: {total_edges:,}")
    print(f"    Unique diseases: {unique_diseases:,}")
    print(f"    Unique targets: {unique_targets:,}")
    print(f"    Score range: {score_stats['min']:.4f} - {score_stats['max']:.4f}")
    print(f"    Score mean: {score_stats['mean']:.4f}, median: {score_stats['median']:.4f}")


def main():
    print("=" * 60)
    print("BUILDING CANCER TARGET-DISEASE EDGE LISTS")
    print("=" * 60)

    check_prerequisites()
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("\nLoading cancer disease crosswalk from Phase 1...")
    cancer_diseases = load_cancer_diseases()
    print(f"  Found {len(cancer_diseases):,} cancer diseases")

    print("\nLoading target index...")
    targets = load_targets()

    # Process each association type
    results = {}
    for assoc_type in ["indirect", "direct"]:
        assoc_path = DATA_DIR / (
            "association_by_overall_indirect" if assoc_type == "indirect"
            else "association_overall_direct"
        )
        if not assoc_path.exists():
            print(f"\nSkipping {assoc_type} (data not downloaded)")
            continue

        print(f"\nProcessing {assoc_type} associations...")
        associations = load_associations(assoc_type)

        df = build_edge_list(cancer_diseases, targets, associations, assoc_type)
        results[assoc_type] = df

        save_edge_list(df, assoc_type)
        print_summary(df, assoc_type)

    # Final summary
    print("\n" + "=" * 60)
    print("EDGE LIST BUILD COMPLETE")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nGenerated files:")
    for f in sorted(OUTPUT_DIR.glob("cancer_associations_*")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.1f} MB)")

    print("\nOutput schema:")
    print("  - diseaseId: EFO/MONDO disease ID")
    print("  - diseaseName: Human-readable disease name")
    print("  - targetId: Ensembl gene ID")
    print("  - approvedSymbol: HGNC gene symbol")
    print("  - score: Overall association score (0-1)")
    print("  - meshIds: MeSH descriptor IDs (comma-separated in CSV)")


if __name__ == "__main__":
    main()
