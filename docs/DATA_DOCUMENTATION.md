# Open Targets Cancer Gene-MeSH Data Documentation

## Overview

This dataset maps cancer gene-disease associations from Open Targets to MeSH (Medical Subject Headings) vocabulary with Entrez Gene IDs for patent matching.

## Data Sources

### 1. Open Targets Platform (v25.12)
- **URL**: https://platform.opentargets.org/
- **Disease index**: 46,960 diseases total, 3,395 cancer
- **Associations**: `association_overall_direct/` - 4.5M gene-disease pairs
- **Cancer = 22.8%** of all OT associations

### 2. MeSH 2025 (Medical Subject Headings)
- **Source**: NLM (National Library of Medicine)
- **File**: `d2025.bin` - raw ASCII descriptor file (30 MB)
- **Extracted live**: C04.588 (Neoplasms by Site) branch
- **URL**: https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/d2025.bin

### 3. NCBI Gene Mapping
- **Source**: NCBI gene2ensembl
- **File**: `gene2ensembl.gz` (~278 MB, filtered to human)
- **Mappings**: 38,278 human Ensembl → Entrez
- **URL**: https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz

---

## Final Output Schema

### `gene_disease_mesh_final.tsv`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `disease_mesh_id` | string | MeSH descriptor ID | D001943 |
| `gene_entrez_id` | int | NCBI Entrez Gene ID | 7157 |
| `ot_score` | float | Max association score (0-1) | 0.843 |
| `evidence_count` | int | Sum of evidence sources | 455 |

**Stats:**
- 171,856 rows
- 146 unique MeSH terms
- 19,275 unique Entrez genes
- Sorted by `ot_score` descending

---

## Crosswalk Schemas

### `crosswalks/disease_mesh_crosswalk.csv`

| Column | Type | Description |
|--------|------|-------------|
| `diseaseId` | string | Open Targets disease ID (EFO/MONDO) |
| `diseaseName` | string | Disease name |
| `meshId` | string | MeSH descriptor ID |
| `mesh_name` | string | MeSH term name |
| `tree_number` | string | MeSH hierarchy path |
| `level` | int | Hierarchy depth (2-9) |

### `crosswalks/ensembl_entrez.csv`

| Column | Type | Description |
|--------|------|-------------|
| `entrezGeneId` | string | NCBI Entrez Gene ID |
| `ensemblGeneId` | string | Ensembl Gene ID |

---

## MeSH Hierarchy

### Tree Structure (C04.588 - Neoplasms by Site)

```
C04.588 - Neoplasms by Site (Level 2)
├── C04.588.149 - Bone Neoplasms
├── C04.588.180 - Breast Neoplasms
├── C04.588.274 - Digestive System Neoplasms
│   ├── C04.588.274.476 - Gastrointestinal Neoplasms
│   │   └── C04.588.274.476.411 - Intestinal Neoplasms
│   │       └── C04.588.274.476.411.307 - Colorectal Neoplasms
├── C04.588.322 - Endocrine Gland Neoplasms
├── C04.588.443 - Head and Neck Neoplasms
├── C04.588.614 - Nervous System Neoplasms
├── C04.588.805 - Skin Neoplasms
├── C04.588.894 - Thoracic Neoplasms
│   └── C04.588.894.797 - Respiratory Tract Neoplasms
│       └── C04.588.894.797.520 - Lung Neoplasms
└── C04.588.945 - Urogenital Neoplasms
```

### Level Distribution

| Level | Example Terms | In Final Data |
|-------|---------------|---------------|
| 2 | Neoplasms by Site | 1 term |
| 3 | Breast Neoplasms, Bone Neoplasms | 15 terms |
| 4 | Liver Neoplasms, Melanoma | 35 terms |
| 5 | Lung Neoplasms, Prostatic Neoplasms | 42 terms |
| 6 | Colorectal Neoplasms, Pancreatic | 32 terms |
| 7+ | Small Cell Lung Carcinoma | 21 terms |

**Recommended granularity: Level 4-5** (clinical trial level)

---

## Data Quality Metrics

### Coverage

| Metric | Value |
|--------|-------|
| Total OT diseases | 46,960 |
| Cancer diseases | 3,395 (7.2%) |
| With MeSH mapping | 627 (18.5% of cancer) |
| Mapped to C04.588 | 181 disease-mesh pairs |

### Entrez Mapping

| Metric | Value |
|--------|-------|
| Gene-mesh pairs before | 174,965 |
| Gene-mesh pairs after | 171,856 |
| Coverage | 98.2% |
| Lost (no Entrez) | 1.8% |

Unmapped genes by biotype:
- lncRNA: 64%
- Pseudogenes: 22%
- Protein-coding: 4%

### Evidence Distribution

| Bucket | Count | % |
|--------|-------|---|
| 1 source | 74,979 | 43.6% |
| 2-5 sources | 55,589 | 32.3% |
| 6-10 | 16,317 | 9.5% |
| 11-50 | 19,408 | 11.3% |
| 51-100 | 2,900 | 1.7% |
| 100+ | 2,663 | 1.5% |

Max: 25,065 sources (power law distribution)

---

## File Inventory

```
data/
├── opentargets/
│   ├── disease/                      # Disease index (1 parquet)
│   ├── target/                       # Gene index (10 parquets, ~75 MB)
│   └── association_overall_direct/   # Associations (20 parquets, ~5 GB)
├── mesh/
│   ├── d2025.bin                     # Raw MeSH 2025 (30 MB)
│   └── mesh_c04_588_site.csv         # Extracted hierarchy (auto-generated)
├── ncbi/
│   └── gene2ensembl.gz               # Ensembl→Entrez mapping (278 MB)
└── processed/
    ├── gene_disease_mesh_final.tsv   # PRIMARY OUTPUT (6.1 MB)
    ├── crosswalks/
    │   ├── disease_mesh_crosswalk.csv
    │   └── ensembl_entrez.csv
    ├── intermediate/
    │   ├── cancer_diseases_mesh_crosswalk.parquet
    │   └── gene_mesh_pre_entrez.parquet
    ├── summaries/
    │   ├── summary_by_mesh_level.csv
    │   ├── mesh_term_summary.csv
    │   └── mesh_level_4_5_summary.csv
    └── audit/
        ├── audit_missing_mesh_report.txt
        └── audit_top_missing_diseases.csv
```

---

## Known Issues & Limitations

### 1. MeSH Coverage Gap (18.5%)
81.5% of cancer diseases lack MeSH mappings. This is **expected** - research ontologies (EFO/MONDO) are more granular than clinical vocabulary (MeSH).

**Audit finding:** The missing diseases have MORE evidence (55% vs 45%), but external crosswalks provide <1% additional coverage. Vocabulary mismatch is fundamental.

### 2. Duplicate Tree Paths (Polyhierarchy)
Same MeSH term can appear in multiple tree locations. We deduplicate to one row per (disease, meshId), keeping most specific level.

### 3. No Time Dimension
Open Targets is a snapshot, not historical. For temporal analysis, use historical OT releases.

### 4. Score Aggregation
When multiple OT diseases map to same MeSH term, we use:
- **MAX score** (strongest association wins)
- **SUM evidenceCount** (total evidence)

---

## Version Info

- **Open Targets**: v25.12 (December 2025)
- **MeSH**: 2025 edition
- **NCBI gene2ensembl**: December 2025
- **Pipeline**: v2.0 (live MeSH extraction, Entrez IDs)
