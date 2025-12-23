# Open Targets Cancer Gene-MeSH Pipeline

## TL;DR for Colleagues

The final site-only output has **174,965 gene-mesh pairs** across **158 anatomical cancer sites** (https://meshb.nlm.nih.gov/record/ui?ui=D009371) (lung, breast, prostate, etc.) - covering **62% of the MeSH C04.588 hierarchy** (146/236 terms; missing ones are rare syndromes, animal models, and umbrella terms with no OT mappings).

**Key processing decisions:**
- **Polyhierarchy handling:** Same MeSH term can appear in multiple tree locations; we deduplicated to one row per (disease, meshId), keeping the most specific level
- **Multi-disease aggregation:** Multiple OT diseases often map to the same MeSH term (e.g., "ureter cancer" + "ureteral neoplasm" → "Ureteral Neoplasms"); we aggregated by (gene, meshId) using **MAX score** and **SUM evidenceCount**

Each row = one gene + one cancer site + aggregated association score. Use the `level` column to control granularity. MeSH provides standardized cancer vocabulary that maps across literature, clinical trials, and pharma research.

| Metric | Value |
|--------|-------|
| Gene-MeSH pairs (final output) | 174,965 |
| Unique genes | ~19,000 |
| MeSH cancer sites | 158 |
| MeSH hierarchy coverage | 62% (146/236) |
| OT diseases with MeSH | 627 of 3,395 (18.5%) |

---

## What This Pipeline Does

Takes Open Targets gene-disease associations and maps them to MeSH (Medical Subject Headings) cancer terms, enabling analysis of pharmaceutical "search behavior" in cancer drug development.

**Input:**
- Open Targets disease index + gene-disease associations
- MeSH 2025 neoplasm hierarchy (C04)

**Output:**
- `cancer_gene_disease_mesh_site_only.parquet` - 174,965 rows, one per (gene, MeSH cancer site)
- Each row has: gene ID, MeSH term, hierarchy level, max association score, total evidence count

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Cancer diseases in Open Targets | 3,395 |
| Diseases with MeSH mappings | 627 (18.5%) |
| Unique MeSH site terms | 158 |
| Gene-MeSH pairs (final output) | 174,965 |
| Unique genes | ~19,000 |

---

## Pipeline Steps

### Phase 1: Extract Cancer Diseases
1. Load Open Targets disease index (~23K diseases)
2. Filter to cancer by checking if `ancestors` contains `EFO_0000616` (neoplasm)
3. Extract MeSH IDs from `dbXRefs` field (Open Targets' own cross-references)
4. Result: 3,395 cancer diseases, 627 with MeSH mappings

### Phase 2: Build Gene-Disease-MeSH Dataset
1. Load gene-disease associations (`association_overall_direct`)
2. Load MeSH C04 (neoplasms) hierarchy with tree numbers and levels
3. Join associations with MeSH hierarchy
4. Filter to site-only (C04.588 anatomical hierarchy)
5. Deduplicate and aggregate (see below)
6. Output final dataset

---

## Key Decisions & Rationale

### 1. MeSH Source: Open Targets dbXRefs Only
**Decision:** Use MeSH IDs from Open Targets' `dbXRefs` field, not external crosswalks.

**Rationale:** OT already curates disease-to-MeSH mappings. Using their mappings ensures consistency with the association data. External crosswalks (UMLS, etc.) would add complexity without clear benefit.

**Trade-off:** Only 18.5% of cancer diseases have MeSH mappings. This is expected - research ontologies (EFO/MONDO) are more granular than clinical vocabulary (MeSH).

### 2. Direct Associations Only (not Indirect)
**Decision:** Use `association_overall_direct` instead of `association_overall_indirect`.

**Rationale:**
- **Direct:** Evidence explicitly links gene to that specific disease
- **Indirect:** Inherited from parent diseases in ontology (gene linked to "Breast Cancer" also counts for parent "Neoplasms")

Direct is stricter and avoids inflated counts from ontology inheritance.

### 3. Site-Only Hierarchy (C04.588)
**Decision:** Primary output filters to C04.588 (anatomical site) hierarchy only.

**Rationale:** MeSH has two parallel cancer classifications:
- **C04.588:** By anatomical site (lung, breast, liver, prostate...)
- **C04.557:** By histologic type (carcinoma, sarcoma, adenoma...)

For pharma research focused on organ-specific drug development, anatomical site is more relevant. The same MeSH term can appear in both hierarchies (polyhierarchy).

### 4. Deduplication: One Row per (Disease, MeSH)
**Decision:** Remove duplicate rows where same disease-MeSH pair appears with different tree numbers.

**Rationale:** A single MeSH concept (e.g., "Pancreatic Neoplasms" D010190) can have multiple tree numbers:
- C04.588.274.761 (Digestive System path)
- C04.588.322.475 (Endocrine Glands path)

These are the same concept, just classified in two places. We keep the most specific (lowest level number). Might be more accurate to call this "broadest" but kind of spltting hairs. 

### 5. Aggregation: Multiple OT Diseases → One MeSH
**Decision:** When multiple Open Targets diseases map to the same MeSH term, aggregate by (gene, meshId) with MAX score and SUM evidenceCount.

**Rationale:** OT has redundant disease definitions from different ontologies:
- "ureter cancer" (MONDO_0008627)
- "ureteral neoplasm" (EFO_0003844)
- Both → "Ureteral Neoplasms" (D014516)

These represent the same clinical concept. Aggregating captures total evidence for that gene-cancer site relationship:
- **MAX score:** If gene strongly associated with ANY variant, it's relevant
- **SUM evidenceCount:** Total evidence across all disease definitions

### 6. Recommended Granularity: Level 5
**Decision:** Recommend MeSH level 5 for most analyses.

**Rationale:**
- Level 3-4: Too broad ("Digestive System Neoplasms")
- Level 5: Clinical trial level ("Lung Neoplasms", "Prostatic Neoplasms")
- Level 6+: Research-specific ("Small Cell Lung Carcinoma")

Level 5 balances specificity with sufficient sample sizes. Users can filter by `level` column as needed.

---

## Output Schema

### Site-Only Final Dataset (`cancer_gene_disease_mesh_site_only.parquet`)

| Column | Type | Description |
|--------|------|-------------|
| `targetId` | string | Ensembl gene ID (e.g., ENSG00000141510) |
| `meshId` | string | MeSH descriptor ID (e.g., D008175) |
| `mesh_name` | string | MeSH term name (e.g., "Lung Neoplasms") |
| `tree_number` | string | MeSH hierarchy path (e.g., C04.588.894.797.520) |
| `level` | int | Hierarchy depth, 3-9 (5 recommended) |
| `score` | float | MAX association score across OT diseases (0-1) |
| `evidenceCount` | int | SUM of evidence counts across OT diseases |

### Site-Only Crosswalk (`cancer_mesh_crosswalk_site_only.csv`)

| Column | Type | Description |
|--------|------|-------------|
| `diseaseId` | string | Open Targets disease ID |
| `diseaseName` | string | Disease name |
| `meshId` | string | MeSH descriptor ID |
| `mesh_name` | string | MeSH term name |
| `tree_number` | string | MeSH hierarchy path |
| `level` | int | Hierarchy depth |

---

## Granularity Examples by Level

| Level | Example Terms | Use Case |
|-------|---------------|----------|
| 3 | Breast Neoplasms, Nervous System Neoplasms | Very broad categories |
| 4 | Melanoma, Ovarian Neoplasms, Liver Neoplasms | Organ-level |
| 5 | Lung Neoplasms, Prostatic Neoplasms, Stomach Neoplasms | **Clinical trial level** |
| 6 | Colorectal Neoplasms, Renal Cell Carcinoma | Specific subtypes |
| 7+ | Small Cell Lung Carcinoma, Non-Small Cell Lung Carcinoma | Research-specific |

---

## How to Use

```python
import pandas as pd

# Load the dataset
df = pd.read_parquet("data/processed/cancer_gene_disease_mesh_site_only.parquet")

# Filter to level 5 for clinical trial granularity
level5 = df[df['level'] == 5]

# Get top genes for lung cancer
lung = df[df['mesh_name'] == 'Lung Neoplasms'].sort_values('score', ascending=False)
print(lung.head(20))

# Aggregate to broader categories (level 4)
level4 = df[df['level'] == 4].groupby('mesh_name').agg({
    'targetId': 'nunique',
    'score': 'mean'
})
```

---

## Regenerating the Data

```bash
# Phase 1: Download (~200MB)
./scripts/download_phase1.sh
python scripts/explore_data.py

# Phase 2: Download (~5GB) and build
./scripts/download_phase2.sh
python scripts/build_mesh_crosswalk.py
```

---

## Known Limitations

1. **18.5% MeSH coverage:** Most OT cancer diseases lack MeSH mappings because research ontologies are more granular than clinical vocabulary. This is a fundamental vocabulary mismatch, not a data quality issue.

2. **No drug data:** This dataset links genes to cancers, not drugs. For drug info, would need to join with additional OT data (e.g., ChEMBL).

3. **Score interpretation:** The 0-1 score combines multiple evidence types. Higher = stronger association, but threshold depends on use case.
