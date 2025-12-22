#!/usr/bin/env python3
"""
Phase 1: Explore Open Targets cancer diseases and MeSH crosswalk.

This script:
1. Loads the disease index from Open Targets
2. Filters to cancer diseases (therapeuticAreas contains EFO_0000616)
3. Extracts MeSH IDs from dbXRefs
4. Prints summary statistics
5. Saves cancer disease list with MeSH crosswalk

Run after: ./download_phase1.sh
"""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Cancer therapeutic area in Open Targets (EFO neoplasm)
CANCER_TA = "EFO_0000616"


def load_diseases() -> pd.DataFrame:
    """Load the disease index from Parquet files."""
    disease_path = DATA_DIR / "disease"
    if not disease_path.exists():
        raise FileNotFoundError(
            f"Disease data not found at {disease_path}. Run ./download_phase1.sh first."
        )

    # Load all parquet files in the directory
    parquet_files = list(disease_path.glob("**/*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {disease_path}")

    dfs = [pd.read_parquet(f) for f in parquet_files]
    return pd.concat(dfs, ignore_index=True)


def filter_cancer_diseases(diseases: pd.DataFrame) -> pd.DataFrame:
    """Filter to diseases where ancestors contains the neoplasm ID (EFO_0000616)."""
    # ancestors is a list column containing parent disease IDs
    def has_neoplasm_ancestor(ancestors):
        if ancestors is None or (isinstance(ancestors, float) and pd.isna(ancestors)):
            return False
        return CANCER_TA in ancestors

    mask = diseases["ancestors"].apply(has_neoplasm_ancestor)
    filtered = diseases[mask].copy()

    # Exclude the top-level neoplasm node itself
    filtered = filtered[filtered["id"] != CANCER_TA]

    return filtered


def extract_mesh_ids(diseases: pd.DataFrame) -> pd.DataFrame:
    """
    Extract MeSH IDs from the dbXRefs field.

    dbXRefs is a list of strings like ["MeSH:D001943", "OMIM:114480", ...]
    We filter to MeSH entries and strip the prefix.
    """
    def get_mesh_ids(xrefs):
        if xrefs is None or (isinstance(xrefs, float) and pd.isna(xrefs)):
            return None
        mesh_ids = []
        for ref in xrefs:
            if ref and ref.lower().startswith("mesh:"):
                mesh_ids.append(ref[5:])  # Strip "MeSH:" prefix
        return mesh_ids if mesh_ids else None

    result = diseases[["id", "name"]].copy()
    result.columns = ["diseaseId", "diseaseName"]
    result["meshIds"] = diseases["dbXRefs"].apply(get_mesh_ids)

    return result


def print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics about the cancer diseases and MeSH mappings."""
    total = len(df)
    with_mesh = df["meshIds"].notna().sum()
    without_mesh = total - with_mesh

    print("\n" + "=" * 60)
    print("OPEN TARGETS CANCER DISEASES SUMMARY")
    print("=" * 60)
    print(f"\nTotal cancer diseases: {total:,}")
    print(f"  - With MeSH mapping: {with_mesh:,} ({100*with_mesh/total:.1f}%)")
    print(f"  - Without MeSH mapping: {without_mesh:,} ({100*without_mesh/total:.1f}%)")

    # Sample some diseases with MeSH
    print("\n" + "-" * 60)
    print("SAMPLE: Diseases with MeSH mappings")
    print("-" * 60)
    sample_with_mesh = df[df["meshIds"].notna()].head(10)
    for _, row in sample_with_mesh.iterrows():
        mesh_str = ", ".join(row["meshIds"]) if row["meshIds"] else "None"
        name = row["diseaseName"][:50] if row["diseaseName"] else "Unknown"
        print(f"  {name:<50} -> {mesh_str}")

    # Sample some diseases without MeSH
    print("\n" + "-" * 60)
    print("SAMPLE: Diseases without MeSH mappings")
    print("-" * 60)
    sample_without_mesh = df[df["meshIds"].isna()].head(10)
    for _, row in sample_without_mesh.iterrows():
        name = row["diseaseName"][:60] if row["diseaseName"] else "Unknown"
        print(f"  {row['diseaseId']}: {name}")

    # MeSH ID distribution
    print("\n" + "-" * 60)
    print("MeSH IDs per disease distribution")
    print("-" * 60)
    mesh_counts = df[df["meshIds"].notna()]["meshIds"].apply(len).value_counts().sort_index()
    for count, num_diseases in mesh_counts.items():
        print(f"  {count} MeSH ID(s): {num_diseases:,} diseases")


def main():
    print("Loading disease index...")
    diseases = load_diseases()
    print(f"  Loaded {len(diseases):,} total diseases")

    print("Filtering to cancer diseases...")
    cancer_diseases = filter_cancer_diseases(diseases)
    print(f"  Found {len(cancer_diseases):,} cancer diseases")

    print("Extracting MeSH IDs...")
    result = extract_mesh_ids(cancer_diseases)

    # Print summary
    print_summary(result)

    # Save outputs
    OUTPUT_DIR.mkdir(exist_ok=True)

    parquet_path = OUTPUT_DIR / "cancer_diseases_mesh_crosswalk.parquet"
    csv_path = OUTPUT_DIR / "cancer_diseases_mesh_crosswalk.csv"

    result.to_parquet(parquet_path, index=False)
    print(f"\nSaved Parquet: {parquet_path}")

    # For CSV, convert list to comma-separated string
    csv_df = result.copy()
    csv_df["meshIds"] = csv_df["meshIds"].apply(
        lambda x: ",".join(x) if x else ""
    )
    csv_df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")

    print("\n" + "=" * 60)
    print("Phase 1 complete!")
    print("Next steps:")
    print("  1. Review the output files")
    print("  2. When ready: ./download_phase2.sh")
    print("  3. Then: python build_edge_list.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
