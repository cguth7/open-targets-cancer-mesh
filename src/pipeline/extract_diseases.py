#!/usr/bin/env python3
"""
Pipeline Step 1: Extract cancer diseases from Open Targets.

This module:
1. Loads the disease index from Open Targets
2. Filters to cancer diseases (ancestors contains EFO_0000616)
3. Extracts MeSH IDs from dbXRefs
4. Saves output for downstream processing
"""

import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import load_config, get_path, ensure_dir


def load_diseases(config: dict) -> pd.DataFrame:
    """Load the disease index from Parquet files."""
    disease_path = Path(config["paths"]["opentargets_dir"]) / "disease"

    if not disease_path.exists():
        raise FileNotFoundError(
            f"Disease data not found at {disease_path}. "
            "Run: make download-phase1"
        )

    parquet_files = list(disease_path.glob("**/*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {disease_path}")

    dfs = [pd.read_parquet(f) for f in parquet_files]
    return pd.concat(dfs, ignore_index=True)


def filter_cancer_diseases(
    diseases: pd.DataFrame,
    cancer_ta: str = "EFO_0000616"
) -> pd.DataFrame:
    """
    Filter to diseases where ancestors contains the neoplasm ID.

    Args:
        diseases: Full disease dataframe
        cancer_ta: Therapeutic area ID for cancer (default: EFO_0000616)

    Returns:
        Filtered dataframe with cancer diseases only
    """
    def has_neoplasm_ancestor(ancestors):
        if ancestors is None or (isinstance(ancestors, float) and pd.isna(ancestors)):
            return False
        return cancer_ta in ancestors

    mask = diseases["ancestors"].apply(has_neoplasm_ancestor)
    filtered = diseases[mask].copy()

    # Exclude the top-level neoplasm node itself
    filtered = filtered[filtered["id"] != cancer_ta]

    return filtered


def extract_mesh_ids(diseases: pd.DataFrame) -> pd.DataFrame:
    """
    Extract MeSH IDs from the dbXRefs field.

    dbXRefs is a list of strings like ["MeSH:D001943", "OMIM:114480", ...]
    We filter to MeSH entries and strip the prefix.

    Returns:
        DataFrame with columns: diseaseId, diseaseName, meshIds (list or None)
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


def run(config: dict | None = None, verbose: bool = True) -> pd.DataFrame:
    """
    Run the disease extraction pipeline step.

    Args:
        config: Configuration dict (loads from file if None)
        verbose: Print progress messages

    Returns:
        DataFrame with cancer diseases and MeSH mappings
    """
    if config is None:
        config = load_config()

    cancer_ta = config.get("opentargets", {}).get("cancer_therapeutic_area", "EFO_0000616")

    if verbose:
        print("Step 1: Extracting cancer diseases")
        print("-" * 40)

    # Load diseases
    if verbose:
        print("  Loading disease index...")
    diseases = load_diseases(config)
    if verbose:
        print(f"    {len(diseases):,} total diseases")

    # Filter to cancer
    if verbose:
        print("  Filtering to cancer diseases...")
    cancer_diseases = filter_cancer_diseases(diseases, cancer_ta)
    if verbose:
        print(f"    {len(cancer_diseases):,} cancer diseases")

    # Extract MeSH IDs
    if verbose:
        print("  Extracting MeSH IDs...")
    result = extract_mesh_ids(cancer_diseases)

    with_mesh = result["meshIds"].notna().sum()
    if verbose:
        print(f"    {with_mesh:,} with MeSH ({with_mesh/len(result)*100:.1f}%)")

    # Save output
    output_dir = ensure_dir(Path(config["paths"]["processed_dir"]) / "intermediate")
    output_path = output_dir / "cancer_diseases_mesh_crosswalk.parquet"
    result.to_parquet(output_path, index=False)

    if verbose:
        print(f"  Saved: {output_path}")

    return result


def main():
    """CLI entry point."""
    config = load_config()
    run(config, verbose=True)


if __name__ == "__main__":
    main()
