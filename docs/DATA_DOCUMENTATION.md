# Open Targets Cancer Data - Crosswalk & Schema Documentation

## Overview

This dataset links gene-disease associations from Open Targets to MeSH (Medical Subject Headings) for granularity control in pharma search behavior analysis.

## Data Sources

### 1. Open Targets Platform (v25.12)
- **URL**: https://platform.opentargets.org/
- **Downloaded**: `association_overall_direct/` - gene-disease association scores
- **Format**: Parquet files (~36MB, 4.5M rows total)
- **Disease ontology**: EFO (Experimental Factor Ontology) with imports from MONDO, Orphanet, HP

### 2. MeSH (Medical Subject Headings) 2025
- **Source**: NLM (National Library of Medicine)
- **Downloaded**: `d2025.bin` - descriptor file
- **Extracted**: `mesh_c04_complete.csv` - all C04 (Neoplasms) terms with tree hierarchy

### 3. MONDO Disease Ontology
- **Source**: https://mondo.monarchinitiative.org/
- **Downloaded**: `mondo.json` - full ontology
- **Extracted**: `mondo_mesh_crosswalk.csv` - official MONDO→MeSH mappings

---

## Crosswalk Cardinalities

### MONDO → MeSH (Official)
| Metric | Count |
|--------|-------|
| Total mappings | 8,379 |
| Unique MONDO IDs | 8,254 |
| Unique MeSH IDs | 8,208 |
| MONDO with 1 MeSH | 8,135 (98.6%) |
| MONDO with 2+ MeSH | 119 |
| MeSH with 1 MONDO | 8,044 (97.9%) |
| MeSH with 2+ MONDO | 164 |

**Cardinality: M:M (but effectively 1:1 for 98%+ of cases)**

### Open Targets dbXRefs → MeSH
| Metric | Count |
|--------|-------|
| Cancer diseases with MeSH | 627 |
| Diseases with 1 MeSH | 614 (97.9%) |
| Diseases with 2+ MeSH | 13 |
| Max MeSH per disease | 3 |
| Unique MeSH IDs | 586 |
| MeSH with 1 disease | 533 (91.0%) |
| MeSH with 2+ diseases | 53 |

**Cardinality: M:M**

Examples of diseases with multiple MeSH:
- `MONDO_0002422` (adamantinoma) → `C562741`, `D050398`
- `MONDO_0003036` (mucoepidermoid carcinoma) → `D018298`, `D018277`
- `MONDO_0015459` (nasopharyngeal carcinoma) → `D000077274`, `D00007727`, `C538339`

Examples of MeSH mapped to multiple diseases:
- `C537296` → ovarian granulosa cell tumor, ovarian granulosa tumour
- `C538339` → nasopharyngeal carcinoma, nasopharyngeal squamous cell carcinoma
- `C562840` → hereditary breast carcinoma, Hereditary breast cancer

### MeSH ID → Tree Numbers
**Important**: A single MeSH descriptor can appear in MULTIPLE locations in the tree!

| Metric | Count |
|--------|-------|
| MeSH terms in C04 | 701 |
| Total tree paths | 1,070 |
| MeSH with 1 tree | 438 (62.5%) |
| MeSH with 2+ trees | 263 (37.5%) |

**Cardinality: 1:M**

This is because MeSH has **parallel hierarchies**:
- **C04.588**: Neoplasms by Site (anatomical location)
- **C04.557**: Neoplasms by Histologic Type (cell type)

Example - `D000077192` (Adenocarcinoma of Lung):
- `C04.557.470.200.025.022` (by histologic type: Carcinoma → Adenocarcinoma)
- `C04.588.894.797.520.055` (by site: Thoracic → Lung)

---

## Schema Definitions

### Final Output: `cancer_gene_disease_mesh.parquet`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `diseaseId` | string | Open Targets disease ID (EFO/MONDO) | `MONDO_0018177` |
| `targetId` | string | Ensembl gene ID | `ENSG00000141510` |
| `score` | float | Association strength (0-1) | `0.7964` |
| `evidenceCount` | int | Number of evidence sources | `42` |
| `diseaseName` | string | Human-readable disease name | `glioblastoma` |
| `meshId` | string | MeSH descriptor ID | `D005909` |
| `mesh_name` | string | MeSH term name | `Glioblastoma` |
| `tree_number` | string | MeSH hierarchy path | `C04.557.465.625.600.380.080.335` |
| `level` | int | Depth in hierarchy (1-9) | `8` |

**Note**: Rows with `meshId = NaN` are diseases without official MeSH mappings.

### Crosswalk: `cancer_mesh_crosswalk.csv`

| Column | Type | Description |
|--------|------|-------------|
| `diseaseId` | string | Open Targets disease ID |
| `diseaseName` | string | Disease name |
| `meshId` | string | MeSH descriptor ID |
| `mesh_name` | string | MeSH term name |
| `tree_number` | string | MeSH tree path |
| `level` | int | Hierarchy depth |

### MeSH Hierarchy: `mesh_c04_complete.csv`

| Column | Type | Description |
|--------|------|-------------|
| `mesh_id` | string | MeSH descriptor ID (D######) |
| `mesh_name` | string | Term name |
| `tree_number` | string | Full tree path |
| `level` | int | Depth (1 = C04, 2 = C04.xxx, etc.) |

---

## MeSH C04 Tree Structure

```
C04 - Neoplasms
├── C04.182 - Cysts
├── C04.445 - Hamartoma
├── C04.557 - Neoplasms by Histologic Type    ← BY CELL TYPE
│   ├── C04.557.337 - Leukemia
│   ├── C04.557.386 - Lymphoma
│   ├── C04.557.435 - Mixed Tissue Neoplasms
│   ├── C04.557.450 - Mesenchymal Neoplasms
│   ├── C04.557.465 - Neuroectodermal Tumors
│   ├── C04.557.470 - Glandular/Epithelial Neoplasms
│   │   └── C04.557.470.200 - Carcinoma
│   └── ...
├── C04.588 - Neoplasms by Site               ← BY ANATOMICAL LOCATION
│   ├── C04.588.033 - Abdominal Neoplasms
│   ├── C04.588.149 - Bone Neoplasms
│   ├── C04.588.180 - Breast Neoplasms
│   ├── C04.588.274 - Digestive System Neoplasms
│   ├── C04.588.322 - Endocrine Gland Neoplasms
│   ├── C04.588.443 - Head/Neck Neoplasms
│   ├── C04.588.614 - Nervous System Neoplasms
│   ├── C04.588.699 - Pelvic Neoplasms
│   ├── C04.588.805 - Skin Neoplasms
│   ├── C04.588.894 - Thoracic Neoplasms
│   └── C04.588.945 - Urogenital Neoplasms
└── ...
```

### Level Distribution in C04

| Level | Example Terms | Count |
|-------|---------------|-------|
| 1 | Neoplasms | 1 |
| 2 | Cysts, Hamartoma | 7 |
| 3 | Breast Neoplasms, Leukemia | 105 |
| 4 | Liver Neoplasms, Melanoma | 191 |
| 5 | Lung, Prostate, Ovarian | 247 |
| 6 | Colorectal, Pancreatic | 213 |
| 7+ | Specific subtypes | 237 |

**Recommended granularity for pharma analysis: Level 4-5**

---

## Official Crosswalk Sources

| Crosswalk | Source | Used | Notes |
|-----------|--------|------|-------|
| EFO/MONDO → MeSH | Open Targets dbXRefs | Yes | Primary source, curated by OT |
| MONDO → MeSH | MONDO ontology xrefs | Yes | Supplementary (+1 disease) |
| Orphanet → MeSH | N/A | N/A | No official crosswalk exists |

**Coverage ceiling**: 627 of 3,395 cancer diseases (18.5%) have official MeSH mappings.

This is expected because MeSH is a **clinical vocabulary** for literature indexing, while EFO/MONDO are **research ontologies** with much finer granularity. Many research-level cancer subtypes (e.g., "BRAF-mutant melanoma") simply don't have MeSH equivalents.

---

## File Inventory

```
data/
├── opentargets/
│   ├── association_by_datasource_direct/   # Not used (by-source breakdown)
│   └── association_overall_direct/         # 20 parquet files, 36MB
├── mesh/
│   ├── d2025.bin                           # Raw MeSH descriptors
│   └── mesh_c04_complete.csv               # 701 C04 terms with trees
├── mondo/
│   ├── mondo.json                          # Full MONDO ontology
│   └── mondo_mesh_crosswalk.csv            # 8,379 MONDO→MeSH mappings
└── processed/
    ├── cancer_diseases_mesh_crosswalk.parquet  # 3,395 OT cancer diseases
    ├── cancer_mesh_crosswalk.csv               # 642 rows, 628 diseases
    ├── cancer_gene_disease_mesh.parquet        # FINAL: 1.15M rows
    ├── cancer_gene_disease_mesh.csv            # Same, CSV format
    ├── summary_by_mesh_level.csv               # Coverage by level
    ├── mesh_term_summary.csv                   # Stats per MeSH term
    └── mesh_level_4_5_summary.csv              # Level 4-5 terms only
```

---

## Known Issues & Limitations

1. **No time dimension**: Open Targets provides current state only, not historical evolution of evidence.

2. **MeSH coverage gap**: 81.5% of cancer diseases lack MeSH mappings (research-level specificity exceeds clinical vocabulary).

3. **Duplicate rows from parallel hierarchies**: Same disease can appear with multiple tree paths (by site AND by histologic type). Use `tree_number.startswith('C04.588')` to filter to site-only.

4. **Supplementary Concept Records (SCRs)**: Some MeSH IDs start with 'C' instead of 'D' - these are not official descriptors but supplementary concepts. They may lack tree numbers.

---

## Version Info

- **Open Targets**: v25.12 (December 2025)
- **MeSH**: 2025 edition
- **MONDO**: Latest as of December 2025
- **Created**: December 2025
