# Open Targets Cancer Data - Next Steps Plan

## Project Goal
Build a dataset for studying how pharma firms "search" in cancer drug development. Need gene-disease association scores crosswalked to MeSH for granularity control.

## What We Have Already

### Downloaded
- `data/opentargets/association_by_datasource_direct/` - 36MB, 4.7M rows (BUT this is broken down by source, not what we need)
- `data/mondo/mondo.json` - 98MB MONDO ontology
- `data/mesh/d2025.bin` - 31MB official MeSH descriptors

### Created
- `data/mesh/mesh_c04_complete.csv` - **701 unique MeSH cancer terms** (all of C04, levels 1-9)
- `data/mondo/mondo_mesh_crosswalk.csv` - 8,379 MONDO→MeSH mappings
- `data/processed/cancer_diseases_mesh_crosswalk.parquet` - 3,395 OT cancer diseases with MeSH IDs (627 have MeSH)
- `data/processed/cancer_mesh_crosswalk.csv` - clean crosswalk (641 rows, 627 diseases, 586 MeSH IDs)

### Key Findings
1. **MeSH has parallel hierarchies**: C04.588 (by site) AND C04.557 (by histologic type). Same cancer can appear in both.
2. **OT provides MeSH for 627/3,395 (18.5%) cancer diseases** - this is close to the ceiling for official mappings
3. **Level 4 MeSH coverage**: 114/191 (60%) of level 4 terms are in OT data
4. **OT disease index IS the official crosswalk** - MeSH IDs come from dbXRefs field

## What Needs To Be Done

### Step 1: Download the RIGHT association file
```bash
# Download association_overall_direct (ONE score per gene-disease pair)
mkdir -p data/opentargets/association_overall_direct
rsync -avz --progress rsync.ebi.ac.uk::pub/databases/opentargets/platform/25.12/output/association_overall_direct/ data/opentargets/association_overall_direct/
```

This gives ONE row per (gene, disease) pair with an overall score - not broken down by datasource.

### Step 2: Filter to cancer diseases
```python
import pandas as pd
import os

# Load all association parquet files
assoc_path = 'data/opentargets/association_overall_direct/'
files = [f for f in os.listdir(assoc_path) if f.endswith('.parquet')]
assoc = pd.concat([pd.read_parquet(os.path.join(assoc_path, f)) for f in files])

# Load cancer disease list
cancer = pd.read_parquet('data/processed/cancer_diseases_mesh_crosswalk.parquet')
cancer_ids = set(cancer['diseaseId'])

# Filter to cancer only
cancer_assoc = assoc[assoc['diseaseId'].isin(cancer_ids)]
```

### Step 3: Join with MeSH crosswalk
```python
# Load clean crosswalk
crosswalk = pd.read_csv('data/processed/cancer_mesh_crosswalk.csv')

# Join
final = cancer_assoc.merge(crosswalk[['diseaseId', 'diseaseName', 'meshId', 'mesh_name', 'tree_number', 'level']],
                           on='diseaseId', how='left')

# Save
final.to_parquet('data/processed/cancer_gene_disease_mesh.parquet')
final.to_csv('data/processed/cancer_gene_disease_mesh.csv', index=False)
```

### Step 4: Create summary by MeSH level
For granularity control, aggregate by MeSH level (3, 4, 5, etc.)

## Expected Output Schema
```
| Column      | Description                           |
|-------------|---------------------------------------|
| targetId    | Ensembl gene ID (ENSG...)             |
| diseaseId   | OT disease ID (MONDO/EFO)             |
| score       | Overall association score (0-1)       |
| diseaseName | Human readable disease name           |
| meshId      | MeSH descriptor ID (D...)             |
| mesh_name   | MeSH term name                        |
| tree_number | MeSH tree path (e.g., C04.588.274)    |
| level       | Hierarchy depth (1-9)                 |
```

## File Locations
```
data/
├── opentargets/
│   ├── association_by_datasource_direct/  # Already downloaded (can delete)
│   └── association_overall_direct/        # NEED TO DOWNLOAD
├── mesh/
│   ├── mesh_c04_complete.csv              # Complete C04 hierarchy (701 terms)
│   └── d2025.bin                          # Raw MeSH data
├── mondo/
│   ├── mondo.json                         # MONDO ontology
│   └── mondo_mesh_crosswalk.csv           # MONDO→MeSH mappings
└── processed/
    ├── cancer_diseases_mesh_crosswalk.parquet  # OT cancer diseases
    ├── cancer_mesh_crosswalk.csv               # Clean crosswalk
    └── cancer_gene_disease_mesh.parquet        # FINAL OUTPUT (to create)
```

## Direct vs Indirect
- **Direct**: Only explicit evidence links (cleaner, recommended for this analysis)
- **Indirect**: Includes inherited associations from disease hierarchy (noisier)

Use DIRECT for studying pharma search behavior.

## Notes on MeSH Levels
| Level | Example | Count in C04 |
|-------|---------|--------------|
| 3 | Breast Neoplasms, Leukemia | 105 |
| 4 | Liver Neoplasms, Melanoma | 191 |
| 5 | Lung, Prostate, Ovarian | 247 |
| 6 | Colorectal | 213 |

Level 4-5 is probably the right granularity for pharma analysis.
