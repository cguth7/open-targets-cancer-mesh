# Open Targets Cancer Gene-Disease-MeSH Dataset

Dataset for studying pharma "search" behavior in cancer drug development. Links gene-disease associations from Open Targets to MeSH for granularity control.

## Quick Start

```bash
# 1. Download data (run these first)
./download_phase1.sh   # Disease index
./download_phase2.sh   # Associations + targets

# 2. Build datasets
python scripts/explore_data.py         # Phase 1: Extract cancer diseases
python scripts/build_mesh_crosswalk.py # Phase 2: Build final dataset
```

## Output Files

| File | Rows | Description |
|------|------|-------------|
| `cancer_gene_disease_mesh.parquet` | 1.38M | Full dataset |
| `cancer_gene_disease_mesh_site_only.parquet` | 200K | MeSH by anatomical site only |
| `cancer_mesh_crosswalk.csv` | 641 | Disease → MeSH mapping |

## Schema

```
diseaseId     | EFO/MONDO disease ID (e.g., MONDO_0005061)
targetId      | Ensembl gene ID (e.g., ENSG00000141510)
score         | Association strength 0-1 (higher = more evidence)
evidenceCount | Number of evidence sources
diseaseName   | Human-readable name
meshId        | MeSH descriptor ID (e.g., D001943) - NULL if no mapping
mesh_name     | MeSH term name
tree_number   | MeSH hierarchy path (e.g., C04.588.180) - NULL if not in C04
level         | Hierarchy depth 1-9
```

## MeSH Crosswalk

**Source: Open Targets `dbXRefs` only** - no external crosswalks.

Coverage:
- 627 of 3,395 cancer diseases (18.5%) have official MeSH mappings
- This is the ceiling for official crosswalks (MeSH is less granular than research ontologies)

MeSH ID types in crosswalk:
- `D######` in C04: Official descriptors with hierarchy (use for granularity analysis)
- `D######` not in C04: Mapped to non-neoplasm MeSH terms
- `C######`: Supplementary Concept Records (no hierarchy)

**For granularity analysis, filter to rows where `tree_number` is not null.**

## MeSH Hierarchy

MeSH has parallel hierarchies for neoplasms:
- **C04.588**: By anatomical site (lung, breast, liver...)
- **C04.557**: By histologic type (carcinoma, adenoma, sarcoma...)

Same cancer can appear in both. Use `_site_only` files if you only want anatomical classification.

### Recommended Granularity: Level 4-5

| Level | Examples | Specificity |
|-------|----------|-------------|
| 3 | Breast Neoplasms, Leukemia | Broad organ systems |
| 4 | Liver Neoplasms, Melanoma | Specific organs |
| 5 | Lung, Prostate, Ovarian | Clinical trial level |
| 6+ | Colorectal subtypes | Research-level |

## File Structure

```
data/
├── opentargets/
│   ├── disease/                        # Disease index
│   └── association_overall_direct/     # Gene-disease scores
├── mesh/
│   ├── d2025.bin                       # Raw MeSH 2025
│   └── mesh_c04_complete.csv           # C04 hierarchy extracted
└── processed/
    ├── cancer_diseases_mesh_crosswalk.parquet  # Phase 1 output
    ├── cancer_mesh_crosswalk.csv               # Disease→MeSH
    ├── cancer_gene_disease_mesh.parquet        # Final dataset
    └── cancer_gene_disease_mesh_site_only.parquet

scripts/
├── explore_data.py          # Phase 1: Extract cancer diseases from OT
├── build_mesh_crosswalk.py  # Phase 2: Build final dataset with MeSH
└── build_edge_list.py       # Alternative: Polars-based edge list builder

docs/
├── DATA_DOCUMENTATION.md    # Detailed schema & cardinality docs
├── LEARNINGS.md             # Project learnings
└── ...
```

## Limitations

1. **No time dimension**: Open Targets is a snapshot, not historical. For temporal analysis, consider ClinicalTrials.gov or historical OT releases.

2. **MeSH coverage ceiling**: 81.5% of cancer diseases lack MeSH mappings because research ontologies (EFO/MONDO) are more granular than clinical vocabulary (MeSH).

3. **Duplicate rows from parallel hierarchies**: A disease can have multiple tree paths. Filter by `tree_number.startswith('C04.588')` for site-only.

## Data Sources

- **Open Targets Platform v25.12**: https://platform.opentargets.org/
- **MeSH 2025**: https://www.nlm.nih.gov/mesh/
- **MONDO**: https://mondo.monarchinitiative.org/
