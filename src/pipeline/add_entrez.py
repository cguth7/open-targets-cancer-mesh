#!/usr/bin/env python3
"""
Pipeline Step 3: Add Entrez Gene IDs and produce final output.

This module:
1. Downloads gene2ensembl from NCBI (if not cached)
2. Filters to human genes (tax_id=9606)
3. Maps Ensembl Gene IDs → Entrez Gene IDs
4. Produces final 4-column TSV for patent matching

Final output columns:
- disease_mesh_id: MeSH descriptor ID (e.g., D001943)
- gene_entrez_id: NCBI Entrez Gene ID (e.g., 7157)
- ot_score: Open Targets association score (0-1)
- evidence_count: Number of evidence sources
"""

import gzip
import urllib.request
import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import load_config, ensure_dir


GENE2ENSEMBL_URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz"
HUMAN_TAX_ID = 9606


def download_gene2ensembl(config: dict, force: bool = False) -> Path:
    """Download gene2ensembl.gz from NCBI."""
    ncbi_dir = ensure_dir(Path(config["paths"]["data_dir"]) / "ncbi")
    output_path = ncbi_dir / "gene2ensembl.gz"

    if output_path.exists() and not force:
        print(f"    Using cached: {output_path}")
        return output_path

    url = config.get("ncbi", {}).get("gene2ensembl_url", GENE2ENSEMBL_URL)
    print(f"    Downloading from {url}...")
    print(f"    (This is ~278 MB, may take a few minutes)")

    urllib.request.urlretrieve(url, output_path)
    print(f"    Saved: {output_path}")

    return output_path


def load_gene2ensembl(gz_path: Path, tax_id: int = HUMAN_TAX_ID) -> pd.DataFrame:
    """Load gene2ensembl and filter to human."""
    print(f"    Loading and filtering to tax_id={tax_id}...")

    with gzip.open(gz_path, 'rt') as f:
        df = pd.read_csv(f, sep='\t', dtype=str)

    df = df[df['#tax_id'] == str(tax_id)].copy()
    df = df.rename(columns={
        '#tax_id': 'tax_id',
        'GeneID': 'entrezGeneId',
        'Ensembl_gene_identifier': 'ensemblGeneId'
    })

    # Keep only gene-level mappings, dedupe
    gene_mapping = df[['entrezGeneId', 'ensemblGeneId']].drop_duplicates()
    gene_mapping = gene_mapping.drop_duplicates(subset=['ensemblGeneId'], keep='first')

    print(f"    {len(gene_mapping):,} human Ensembl → Entrez mappings")
    return gene_mapping


def run(config: dict | None = None, verbose: bool = True) -> pd.DataFrame:
    """
    Run the Entrez mapping and produce final output.

    Returns:
        Final 4-column DataFrame
    """
    if config is None:
        config = load_config()

    processed_dir = Path(config["paths"]["processed_dir"])
    crosswalks_dir = ensure_dir(processed_dir / "crosswalks")

    if verbose:
        print("Step 3: Adding Entrez Gene IDs")
        print("-" * 40)

    # Load gene-mesh dataset from Step 2
    input_path = processed_dir / "intermediate" / "gene_mesh_pre_entrez.parquet"
    if not input_path.exists():
        raise FileNotFoundError(f"Run Step 2 first: {input_path}")

    if verbose:
        print("  Loading gene-mesh dataset...")
    df = pd.read_parquet(input_path)
    if verbose:
        print(f"    {len(df):,} gene-mesh pairs")

    # Download/load Entrez mapping
    if verbose:
        print("  Loading Entrez mapping...")
    gz_path = download_gene2ensembl(config)
    entrez_map = load_gene2ensembl(gz_path)

    # Save crosswalk
    entrez_map.to_csv(crosswalks_dir / "ensembl_entrez.csv", index=False)

    # Merge
    if verbose:
        print("  Mapping Ensembl → Entrez...")
    df = df.merge(
        entrez_map.rename(columns={'ensemblGeneId': 'targetId'}),
        on='targetId',
        how='left'
    )

    # Drop rows without Entrez ID
    before = len(df)
    df = df.dropna(subset=['entrezGeneId'])
    if verbose:
        print(f"    {len(df):,}/{before:,} have Entrez ID ({len(df)/before*100:.1f}%)")

    # Convert Entrez to int
    df['entrezGeneId'] = df['entrezGeneId'].astype(int)

    # Create final 4-column output
    final = df[['meshId', 'entrezGeneId', 'score', 'evidenceCount']].copy()
    final.columns = ['disease_mesh_id', 'gene_entrez_id', 'ot_score', 'evidence_count']

    # Sort by score descending
    final = final.sort_values('ot_score', ascending=False).reset_index(drop=True)

    # Save final output
    output_path = processed_dir / "gene_disease_mesh_final.tsv"
    final.to_csv(output_path, sep='\t', index=False)

    if verbose:
        print(f"  Saved: {output_path}")
        print(f"    {len(final):,} rows")
        print(f"    {final['disease_mesh_id'].nunique()} MeSH terms")
        print(f"    {final['gene_entrez_id'].nunique()} genes")

    return final


def main():
    """CLI entry point."""
    config = load_config()
    run(config, verbose=True)


if __name__ == "__main__":
    main()
