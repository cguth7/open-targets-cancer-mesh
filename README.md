# Open Targets Cancer Gene-Disease-MeSH Dataset

Dataset for studying pharma "search" behavior in cancer drug development. Links gene-disease associations from Open Targets to MeSH for granularity control, with Entrez Gene IDs for patent matching.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Download all required data (~5.5 GB total)
make download-all

# Run the complete pipeline
make pipeline

# Or run individual steps
make download-phase1   # Disease & target indexes (~75 MB)
make download-phase2   # Associations (~5 GB)
make download-entrez   # NCBI gene2ensembl (~278 MB)
```

## Pipeline Steps

| Step | Command | Output |
|------|---------|--------|
| 1. Extract diseases | `python -m src.pipeline.extract_diseases` | `cancer_diseases_mesh_crosswalk.parquet` |
| 2. Build crosswalk | `python -m src.pipeline.build_crosswalk` | `cancer_gene_disease_mesh*.parquet` |
| 3. Add Entrez IDs | `python -m src.pipeline.add_entrez` | `*_with_entrez.parquet` |
| Audit | `python -m src.analysis.audit_missing_mesh` | `audit_missing_mesh_report.txt` |

## Output Files

| File | Rows | Description |
|------|------|-------------|
| `cancer_gene_mesh_site_only_with_entrez.parquet` | 175K | **Primary output**: Gene-MeSH pairs with Entrez IDs |
| `cancer_gene_disease_mesh.parquet` | 1.38M | Full dataset (all associations) |
| `cancer_mesh_crosswalk.csv` | 641 | Disease → MeSH mapping |
| `ensembl_entrez_crosswalk.csv` | ~40K | Ensembl → Entrez gene mapping |

## Schema

### Site-Only with Entrez (recommended for patent matching)

```
targetId      | Ensembl gene ID (e.g., ENSG00000141510)
entrezGeneId  | NCBI Entrez gene ID (e.g., 7157) - for patent matching
meshId        | MeSH descriptor ID (e.g., D001943)
mesh_name     | MeSH term name (e.g., "Breast Neoplasms")
tree_number   | MeSH hierarchy path (e.g., C04.588.180)
level         | Hierarchy depth 3-9
score         | Max association strength 0-1
evidenceCount | Sum of evidence across OT diseases
```

## MeSH Coverage

**Source: Open Targets `dbXRefs` only** - curated mappings, no external crosswalks.

| Metric | Value |
|--------|-------|
| Total cancer diseases | 3,395 |
| With MeSH mapping | 627 (18.5%) |
| Unique MeSH C04 terms | ~150 |
| Gene-MeSH pairs (site-only) | 174,965 |

### Why Only 18% Coverage?

This is **by design**, not a data quality issue. See [AUDIT_FINDINGS.md](docs/AUDIT_FINDINGS.md).

- EFO/MONDO are research ontologies (granular)
- MeSH is clinical vocabulary (broader)
- "breast carcinoma, hormone-sensitive" ≠ "Breast Neoplasms"
- The 18% represents "clinically mappable" diseases

## MeSH Hierarchy

MeSH has parallel hierarchies for neoplasms:
- **C04.588**: By anatomical site (lung, breast, liver...)
- **C04.557**: By histologic type (carcinoma, adenoma, sarcoma...)

Use `*_site_only*` files for anatomical classification only.

### Recommended Granularity: Level 4-5

| Level | Examples | Use Case |
|-------|----------|----------|
| 3 | Breast Neoplasms, Leukemia | Broad categories |
| 4 | Liver Neoplasms, Melanoma | Clinical trials |
| 5 | Lung, Prostate, Ovarian | Specific targets |

## Project Structure

```
├── config.yaml              # Pipeline configuration
├── Makefile                 # Build automation
├── requirements.txt         # Python dependencies
│
├── src/
│   ├── pipeline/
│   │   ├── extract_diseases.py   # Step 1: Extract cancer diseases
│   │   ├── build_crosswalk.py    # Step 2: Build gene-disease-MeSH
│   │   ├── add_entrez.py         # Step 3: Add Entrez gene IDs
│   │   └── run_all.py            # Run complete pipeline
│   ├── analysis/
│   │   └── audit_missing_mesh.py # Investigate MeSH coverage
│   └── utils/
│       └── config.py             # Configuration loader
│
├── scripts/                 # Legacy scripts (still work)
│   ├── explore_data.py
│   └── build_mesh_crosswalk.py
│
├── data/
│   ├── opentargets/         # Downloaded OT data
│   ├── mesh/                # MeSH hierarchy
│   ├── ncbi/                # gene2ensembl
│   └── processed/           # Pipeline outputs
│
└── docs/
    ├── AUDIT_FINDINGS.md    # MeSH coverage analysis
    ├── PIPELINE_SUMMARY.md  # Architecture docs
    └── DATA_DOCUMENTATION.md
```

## Configuration

Edit `config.yaml` to customize:

```yaml
paths:
  data_dir: data
  processed_dir: data/processed

pipeline:
  site_only: true           # Use C04.588 anatomical hierarchy only
  include_entrez: true      # Add Entrez gene IDs

mesh:
  site_prefix: "C04.588"    # Anatomical site hierarchy
```

## Make Commands

```bash
make help           # Show all commands
make download-all   # Download all data
make pipeline       # Run complete pipeline
make audit          # Run MeSH coverage audit
make clean          # Remove processed outputs
```

## Data Sources

- **Open Targets Platform v25.12**: https://platform.opentargets.org/
- **MeSH 2025**: https://www.nlm.nih.gov/mesh/
- **NCBI gene2ensembl**: https://ftp.ncbi.nlm.nih.gov/gene/DATA/

## Limitations

1. **18% MeSH coverage**: Research ontologies are more granular than clinical vocabulary. This is expected. See [AUDIT_FINDINGS.md](docs/AUDIT_FINDINGS.md).

2. **No time dimension**: Open Targets is a snapshot. For temporal analysis, use historical OT releases or ClinicalTrials.gov.

3. **Entrez coverage**: ~95% of genes have Entrez IDs. Some Ensembl genes lack NCBI mappings.
