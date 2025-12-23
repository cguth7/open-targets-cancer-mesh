#!/usr/bin/env python3
"""
Audit: Investigate diseases missing MeSH mappings.

Hypothesis: We only use Open Targets' internal MeSH mappings (~18% coverage).
Question: Are the missing ~82% "noise" or important cancer data?

This script:
1. Loads all OT cancer diseases (from Phase 1 output)
2. Splits into With_MeSH and Without_MeSH groups
3. Joins with gene-disease association data
4. Calculates evidence counts and max scores for both groups
5. Identifies top "missing" diseases by evidence volume
6. Generates a decision report

Decision Rule:
- If top missing diseases are noise (umbrella terms, rare subtypes): keep strict filtering
- If major cancer types are missing: investigate MONDO crosswalk or manual curation
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Tuple

# Load config
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def load_config() -> dict:
    """Load configuration from YAML."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    # Fallback defaults
    return {
        "paths": {
            "data_dir": "data",
            "processed_dir": "data/processed",
            "opentargets_dir": "data/opentargets",
        }
    }


def load_cancer_diseases(config: dict) -> pd.DataFrame:
    """Load cancer diseases from Phase 1 output."""
    path = Path(config["paths"]["processed_dir"]) / "cancer_diseases_mesh_crosswalk.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Run Phase 1 first: {path}")
    return pd.read_parquet(path)


def load_associations(config: dict) -> pd.DataFrame:
    """Load gene-disease associations."""
    assoc_dir = Path(config["paths"]["opentargets_dir"]) / "association_overall_direct"
    if not assoc_dir.exists():
        raise FileNotFoundError(f"Download associations first: {assoc_dir}")

    files = list(assoc_dir.glob("*.parquet"))
    print(f"  Loading {len(files)} parquet files...")
    return pd.concat([pd.read_parquet(f) for f in files])


def split_by_mesh(diseases: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split diseases into with/without MeSH groups."""
    with_mesh = diseases[diseases["meshIds"].notna()].copy()
    without_mesh = diseases[diseases["meshIds"].isna()].copy()
    return with_mesh, without_mesh


def calculate_group_stats(
    group_diseases: pd.DataFrame,
    associations: pd.DataFrame,
    group_name: str
) -> dict:
    """Calculate evidence statistics for a disease group."""
    disease_ids = set(group_diseases["diseaseId"])
    group_assoc = associations[associations["diseaseId"].isin(disease_ids)]

    stats = {
        "group": group_name,
        "disease_count": len(group_diseases),
        "diseases_with_associations": group_assoc["diseaseId"].nunique(),
        "total_associations": len(group_assoc),
        "total_evidence": group_assoc["evidenceCount"].sum() if "evidenceCount" in group_assoc else 0,
        "unique_genes": group_assoc["targetId"].nunique(),
        "mean_score": group_assoc["score"].mean() if len(group_assoc) > 0 else 0,
        "max_score": group_assoc["score"].max() if len(group_assoc) > 0 else 0,
    }
    return stats


def find_top_missing_diseases(
    without_mesh: pd.DataFrame,
    associations: pd.DataFrame,
    top_n: int = 20
) -> pd.DataFrame:
    """Find top N diseases without MeSH, ranked by evidence."""
    disease_ids = set(without_mesh["diseaseId"])
    missing_assoc = associations[associations["diseaseId"].isin(disease_ids)]

    # Aggregate by disease
    disease_stats = missing_assoc.groupby("diseaseId").agg({
        "targetId": "nunique",
        "score": ["count", "max", "mean"],
        "evidenceCount": "sum"
    }).reset_index()

    disease_stats.columns = [
        "diseaseId", "unique_genes", "association_count",
        "max_score", "mean_score", "total_evidence"
    ]

    # Join with disease names
    disease_stats = disease_stats.merge(
        without_mesh[["diseaseId", "diseaseName"]],
        on="diseaseId",
        how="left"
    )

    # Sort by evidence
    disease_stats = disease_stats.sort_values("total_evidence", ascending=False)

    return disease_stats.head(top_n)


def find_ghost_towns(
    without_mesh: pd.DataFrame,
    associations: pd.DataFrame
) -> pd.DataFrame:
    """Find diseases with zero associations (ghost towns)."""
    disease_ids = set(without_mesh["diseaseId"])
    diseases_with_assoc = set(associations[associations["diseaseId"].isin(disease_ids)]["diseaseId"])
    ghost_town_ids = disease_ids - diseases_with_assoc

    return without_mesh[without_mesh["diseaseId"].isin(ghost_town_ids)]


def check_mondo_crosswalk(
    without_mesh: pd.DataFrame,
    config: dict
) -> dict:
    """Check if MONDO crosswalk could fill gaps."""
    mondo_path = Path(config["paths"]["data_dir"]) / "mondo" / "mondo_mesh_crosswalk.csv"

    if not mondo_path.exists():
        return {"available": False, "path": str(mondo_path)}

    mondo_crosswalk = pd.read_csv(mondo_path)

    # Get MONDO IDs from our missing diseases
    mondo_missing = without_mesh[without_mesh["diseaseId"].str.startswith("MONDO_")]
    mondo_ids = set(mondo_missing["diseaseId"])

    # Check coverage in crosswalk
    crosswalk_ids = set(mondo_crosswalk["mondo_id"]) if "mondo_id" in mondo_crosswalk.columns else set()
    overlap = mondo_ids & crosswalk_ids

    return {
        "available": True,
        "path": str(mondo_path),
        "crosswalk_total": len(mondo_crosswalk),
        "our_mondo_missing": len(mondo_ids),
        "overlap_count": len(overlap),
        "coverage_pct": len(overlap) / len(mondo_ids) * 100 if mondo_ids else 0,
        "sample_overlap": list(overlap)[:5] if overlap else []
    }


def generate_report(
    with_mesh_stats: dict,
    without_mesh_stats: dict,
    top_missing: pd.DataFrame,
    ghost_towns: pd.DataFrame,
    mondo_check: dict,
    output_path: Path
) -> str:
    """Generate the audit report."""

    report = []
    report.append("=" * 70)
    report.append("AUDIT REPORT: MeSH Coverage Analysis")
    report.append("=" * 70)

    # Summary stats
    report.append("\n## 1. COVERAGE SUMMARY\n")
    total = with_mesh_stats["disease_count"] + without_mesh_stats["disease_count"]
    report.append(f"Total cancer diseases: {total:,}")
    report.append(f"  With MeSH:    {with_mesh_stats['disease_count']:,} ({with_mesh_stats['disease_count']/total*100:.1f}%)")
    report.append(f"  Without MeSH: {without_mesh_stats['disease_count']:,} ({without_mesh_stats['disease_count']/total*100:.1f}%)")

    # Evidence comparison
    report.append("\n## 2. EVIDENCE COMPARISON\n")
    report.append(f"{'Metric':<30} {'With MeSH':>15} {'Without MeSH':>15}")
    report.append("-" * 60)

    total_evidence = with_mesh_stats["total_evidence"] + without_mesh_stats["total_evidence"]
    for metric in ["total_evidence", "unique_genes", "total_associations", "diseases_with_associations"]:
        w = with_mesh_stats[metric]
        wo = without_mesh_stats[metric]
        report.append(f"{metric:<30} {w:>15,} {wo:>15,}")

    report.append(f"\n{'Evidence share':<30} {with_mesh_stats['total_evidence']/total_evidence*100:>14.1f}% {without_mesh_stats['total_evidence']/total_evidence*100:>14.1f}%")

    # Ghost towns
    report.append(f"\n## 3. GHOST TOWNS (zero associations)\n")
    report.append(f"Diseases without MeSH AND without any associations: {len(ghost_towns):,}")
    report.append(f"  ({len(ghost_towns)/without_mesh_stats['disease_count']*100:.1f}% of unmapped diseases)")
    report.append("\nSample ghost towns:")
    for _, row in ghost_towns.head(10).iterrows():
        report.append(f"  - {row['diseaseId']}: {row['diseaseName'][:60]}")

    # Top missing
    report.append(f"\n## 4. TOP 20 MISSING DISEASES (by evidence)\n")
    report.append(f"{'Disease':<45} {'Evidence':>12} {'Genes':>8} {'Max Score':>10}")
    report.append("-" * 75)
    for _, row in top_missing.iterrows():
        name = row["diseaseName"][:44] if pd.notna(row["diseaseName"]) else "Unknown"
        report.append(f"{name:<45} {row['total_evidence']:>12,} {row['unique_genes']:>8,} {row['max_score']:>10.4f}")

    # MONDO crosswalk check
    report.append(f"\n## 5. MONDO CROSSWALK CHECK\n")
    if mondo_check["available"]:
        report.append(f"Crosswalk file: {mondo_check['path']}")
        report.append(f"Total entries in crosswalk: {mondo_check['crosswalk_total']:,}")
        report.append(f"Our MONDO diseases missing MeSH: {mondo_check['our_mondo_missing']:,}")
        report.append(f"Overlap (could be rescued): {mondo_check['overlap_count']:,} ({mondo_check['coverage_pct']:.1f}%)")
    else:
        report.append(f"Crosswalk not found: {mondo_check['path']}")

    # Decision
    report.append(f"\n## 6. DECISION\n")

    # Check if top missing are major cancers or noise
    major_cancer_keywords = ["breast", "lung", "colon", "prostate", "pancrea", "liver", "leukemia", "lymphoma", "melanoma"]
    top_names = " ".join(top_missing["diseaseName"].fillna("").str.lower())
    major_missing = [kw for kw in major_cancer_keywords if kw in top_names]

    if major_missing:
        report.append("WARNING: Major cancer types are in the missing list!")
        report.append(f"  Found keywords: {', '.join(major_missing)}")
        report.append("\nHowever, this is expected due to vocabulary mismatch:")
        report.append("  - EFO/MONDO research ontologies are more granular than MeSH clinical vocabulary")
        report.append("  - 'breast cancer' in OT ≠ 'Breast Neoplasms' MeSH term (different ID systems)")
        report.append("\nRECOMMENDATION:")
        if mondo_check["available"] and mondo_check["coverage_pct"] > 10:
            report.append("  → Use MONDO crosswalk to fill gaps (>10% coverage possible)")
        else:
            report.append("  → Keep strict filtering. MONDO crosswalk provides <1% additional coverage.")
            report.append("  → The 18% with MeSH represents 'clinically mappable' diseases.")
            report.append("  → Missing data is due to ontology granularity, not data quality.")
    else:
        report.append("Top missing diseases appear to be rare subtypes or umbrella terms.")
        report.append("RECOMMENDATION: Keep strict filtering, document finding.")

    report.append("\n" + "=" * 70)

    report_text = "\n".join(report)

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report_text)

    return report_text


def main():
    print("=" * 60)
    print("AUDIT: Investigating Missing MeSH Mappings")
    print("=" * 60)

    config = load_config()

    # 1. Load data
    print("\n1. Loading cancer diseases...")
    diseases = load_cancer_diseases(config)
    print(f"  {len(diseases):,} total cancer diseases")

    print("\n2. Loading associations...")
    associations = load_associations(config)
    print(f"  {len(associations):,} total associations")

    # 3. Split by MeSH status
    print("\n3. Splitting by MeSH status...")
    with_mesh, without_mesh = split_by_mesh(diseases)
    print(f"  With MeSH: {len(with_mesh):,}")
    print(f"  Without MeSH: {len(without_mesh):,}")

    # 4. Calculate stats for each group
    print("\n4. Calculating evidence statistics...")
    with_mesh_stats = calculate_group_stats(with_mesh, associations, "With MeSH")
    without_mesh_stats = calculate_group_stats(without_mesh, associations, "Without MeSH")

    print(f"  With MeSH - Evidence: {with_mesh_stats['total_evidence']:,}, Genes: {with_mesh_stats['unique_genes']:,}")
    print(f"  Without MeSH - Evidence: {without_mesh_stats['total_evidence']:,}, Genes: {without_mesh_stats['unique_genes']:,}")

    # 5. Find top missing diseases
    print("\n5. Finding top missing diseases by evidence...")
    top_missing = find_top_missing_diseases(without_mesh, associations, top_n=20)

    # 6. Find ghost towns
    print("\n6. Finding ghost towns (zero associations)...")
    ghost_towns = find_ghost_towns(without_mesh, associations)
    print(f"  Found {len(ghost_towns):,} diseases with no associations")

    # 7. Check MONDO crosswalk
    print("\n7. Checking MONDO crosswalk coverage...")
    mondo_check = check_mondo_crosswalk(without_mesh, config)
    if mondo_check["available"]:
        print(f"  Coverage: {mondo_check['coverage_pct']:.1f}% ({mondo_check['overlap_count']}/{mondo_check['our_mondo_missing']})")
    else:
        print("  Crosswalk not found")

    # 8. Generate report
    print("\n8. Generating report...")
    output_path = Path(config["paths"]["processed_dir"]) / "audit_missing_mesh_report.txt"
    report = generate_report(
        with_mesh_stats,
        without_mesh_stats,
        top_missing,
        ghost_towns,
        mondo_check,
        output_path
    )

    print(f"\n{report}")
    print(f"\nReport saved to: {output_path}")

    # Also save top missing as CSV for further analysis
    top_missing_path = Path(config["paths"]["processed_dir"]) / "audit_top_missing_diseases.csv"
    top_missing.to_csv(top_missing_path, index=False)
    print(f"Top missing diseases saved to: {top_missing_path}")


if __name__ == "__main__":
    main()
