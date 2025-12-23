#!/usr/bin/env python3
"""
Extract MeSH C04 (Neoplasms) hierarchy from raw MeSH descriptor file.

Downloads d2025.bin from NLM if not present, then extracts the C04 branch
(or C04.588 site-only branch) into a clean CSV.

MeSH 2025 source: https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/d2025.bin
"""

import re
import urllib.request
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import load_config, ensure_dir


MESH_URL = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/d2025.bin"


def download_mesh(config: dict, force: bool = False) -> Path:
    """Download MeSH descriptor file if not present."""
    mesh_dir = ensure_dir(Path(config["paths"]["mesh_dir"]))
    mesh_path = mesh_dir / "d2025.bin"

    if mesh_path.exists() and not force:
        print(f"    Using cached: {mesh_path}")
        return mesh_path

    print(f"    Downloading MeSH 2025 from NLM (~30 MB)...")
    urllib.request.urlretrieve(MESH_URL, mesh_path)
    print(f"    Saved: {mesh_path}")

    return mesh_path


def parse_mesh_file(mesh_path: Path) -> list[dict]:
    """
    Parse MeSH ASCII descriptor file.

    Extracts:
    - UI: Unique identifier (D######)
    - MH: MeSH Heading (name)
    - MN: Tree number(s) - can have multiple per descriptor
    """
    records = []
    current = {}

    with open(mesh_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()

            if line == '*NEWRECORD':
                if current.get('UI') and current.get('MN'):
                    records.append(current)
                current = {'MN': []}
            elif line.startswith('UI = '):
                current['UI'] = line[5:]
            elif line.startswith('MH = '):
                current['MH'] = line[5:]
            elif line.startswith('MN = '):
                current['MN'].append(line[5:])

    # Don't forget last record
    if current.get('UI') and current.get('MN'):
        records.append(current)

    return records


def extract_c04_hierarchy(
    records: list[dict],
    prefix: str = "C04"
) -> pd.DataFrame:
    """
    Extract neoplasm hierarchy (C04 branch).

    Args:
        records: Parsed MeSH records
        prefix: Tree prefix to filter (C04 = all neoplasms, C04.588 = site only)

    Returns:
        DataFrame with mesh_id, mesh_name, tree_number, level
    """
    rows = []

    for rec in records:
        mesh_id = rec['UI']
        mesh_name = rec.get('MH', '')

        for tree_num in rec['MN']:
            if tree_num.startswith(prefix):
                level = tree_num.count('.') + 1
                rows.append({
                    'mesh_id': mesh_id,
                    'mesh_name': mesh_name,
                    'tree_number': tree_num,
                    'level': level
                })

    df = pd.DataFrame(rows)
    df = df.sort_values(['tree_number', 'mesh_id']).reset_index(drop=True)

    return df


def run(config: dict | None = None, prefix: str = "C04.588", verbose: bool = True) -> pd.DataFrame:
    """
    Extract MeSH hierarchy from raw file.

    Args:
        config: Configuration dict
        prefix: Tree prefix (C04 = all neoplasms, C04.588 = site only)
        verbose: Print progress

    Returns:
        DataFrame with mesh hierarchy
    """
    if config is None:
        config = load_config()

    if verbose:
        print("Extracting MeSH hierarchy")
        print("-" * 40)

    # Download if needed
    if verbose:
        print("  Checking MeSH source file...")
    mesh_path = download_mesh(config)

    # Parse
    if verbose:
        print("  Parsing MeSH descriptors...")
    records = parse_mesh_file(mesh_path)
    if verbose:
        print(f"    {len(records):,} total descriptors")

    # Extract C04 branch
    if verbose:
        print(f"  Extracting {prefix} hierarchy...")
    hierarchy = extract_c04_hierarchy(records, prefix)
    if verbose:
        print(f"    {len(hierarchy):,} tree paths")
        print(f"    {hierarchy['mesh_id'].nunique():,} unique terms")
        print(f"    Levels: {hierarchy['level'].min()}-{hierarchy['level'].max()}")

    # Save
    mesh_dir = ensure_dir(Path(config["paths"]["mesh_dir"]))
    if prefix == "C04":
        output_path = mesh_dir / "mesh_c04_complete.csv"
    elif prefix == "C04.588":
        output_path = mesh_dir / "mesh_c04_588_site.csv"
    else:
        output_path = mesh_dir / f"mesh_{prefix.replace('.', '_')}.csv"

    hierarchy.to_csv(output_path, index=False)
    if verbose:
        print(f"  Saved: {output_path}")

    return hierarchy


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract MeSH hierarchy")
    parser.add_argument("--prefix", default="C04.588", help="Tree prefix (C04 or C04.588)")
    parser.add_argument("--full", action="store_true", help="Extract full C04 (not just site)")
    args = parser.parse_args()

    prefix = "C04" if args.full else args.prefix
    config = load_config()
    run(config, prefix=prefix, verbose=True)


if __name__ == "__main__":
    main()
