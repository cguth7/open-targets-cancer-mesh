# Open Targets Cancer Gene-MeSH Pipeline

## TL;DR

Maps cancer gene-disease associations from Open Targets to MeSH vocabulary with Entrez Gene IDs for patent matching.

**Final Output:** `gene_disease_mesh_final.tsv`
```
disease_mesh_id    gene_entrez_id    ot_score    evidence_count
D018761            4221              0.865       3007
D001943            675               0.843       455
```

| Metric | Value |
|--------|-------|
| Gene-MeSH pairs | 171,856 |
| Unique Entrez genes | 19,275 |
| Unique MeSH terms | 146 |
| Entrez coverage | 98.2% |

---

## Data Funnel

| Stage | Diseases | Associations | % of OT |
|-------|----------|--------------|---------|
| **Total OT** | 46,960 | 4,492,971 | 100% |
| **Cancer only** | 3,395 (7.2%) | 1,023,182 | 22.8% |
| **With MeSH** | 627 (18.5% of cancer) | — | — |
| **Final output** | 146 MeSH terms | 171,856 pairs | 3.8% |

---

## Pipeline Steps

### Step 1: Extract Cancer Diseases
**Script:** `src/pipeline/extract_diseases.py`

1. Load OT disease index (46,960 diseases)
2. Filter where `ancestors` contains `EFO_0000616` (neoplasm) → 3,395 cancer diseases
3. Extract MeSH IDs from `dbXRefs` field → 627 have mappings (18.5%)
4. Save to `intermediate/cancer_diseases_mesh_crosswalk.parquet`

### Step 2: Extract MeSH Hierarchy & Build Crosswalk
**Script:** `src/pipeline/build_crosswalk.py`

1. **Extract MeSH C04.588 LIVE** from `d2025.bin` (MeSH 2025 raw file)
   - Parse ASCII descriptor file
   - Filter to C04.588 (Neoplasms by Site) branch
   - Output: 271 tree paths, 236 unique terms
2. Load gene-disease associations (4.5M rows)
3. Join diseases with MeSH hierarchy
4. Dedupe: one row per (disease, meshId), keep most specific level
5. Aggregate by (gene, meshId): MAX score, SUM evidenceCount
6. Save to `intermediate/gene_mesh_pre_entrez.parquet`

### Step 3: Add Entrez Gene IDs
**Script:** `src/pipeline/add_entrez.py`

1. Download `gene2ensembl.gz` from NCBI (~278 MB)
2. Filter to human (tax_id=9606) → 38,278 mappings
3. Map Ensembl → Entrez (98.2% coverage)
4. Drop unmapped genes (mostly lncRNAs and pseudogenes)
5. Output final 4-column TSV

---

## Key Decisions

### 1. MeSH Source: Live Extraction from d2025.bin
**Decision:** Extract C04.588 hierarchy directly from raw MeSH 2025 file at pipeline runtime.

**Rationale:** Reproducible, no stale pre-extracted CSVs, easy to update when MeSH releases new version.

### 2. Site-Only Hierarchy (C04.588)
**Decision:** Filter to anatomical site classification only.

**Rationale:** MeSH has parallel hierarchies:
- **C04.588:** By anatomical site (lung, breast, liver)
- **C04.557:** By histologic type (carcinoma, sarcoma)

For pharma/patent matching, anatomical site is more relevant.

### 3. Entrez Gene IDs (not Ensembl)
**Decision:** Map Ensembl → Entrez as final gene identifier.

**Rationale:** Patents and NCBI databases use Entrez IDs. Ensembl IDs are less common outside genomics.

### 4. dbXRefs Only (No External Crosswalks)
**Decision:** Use MeSH IDs from OT's `dbXRefs` field only.

**Rationale:**
- Curated mappings from Open Targets
- External crosswalks (MONDO) provide <1% additional coverage
- Vocabulary mismatch is fundamental, not fixable

### 5. Aggregation Strategy
**Decision:** Multiple OT diseases → same MeSH term: MAX score, SUM evidenceCount.

**Rationale:** OT has redundant diseases from different ontologies (e.g., "ureter cancer" + "ureteral neoplasm" → "Ureteral Neoplasms"). Aggregating captures total evidence.

---

## Output Schema

### Final Output: `gene_disease_mesh_final.tsv`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `disease_mesh_id` | string | MeSH descriptor ID | D001943 |
| `gene_entrez_id` | int | NCBI Entrez Gene ID | 7157 |
| `ot_score` | float | Max association score (0-1) | 0.843 |
| `evidence_count` | int | Sum of evidence sources | 455 |

### Crosswalks

| File | Description |
|------|-------------|
| `crosswalks/disease_mesh_crosswalk.csv` | OT disease → MeSH mapping |
| `crosswalks/ensembl_entrez.csv` | Ensembl → Entrez gene mapping |

---

## Evidence Count Distribution

Classic power law - most pairs have few sources, heavy tail has monsters:

| Bucket | Count | % |
|--------|-------|---|
| 1 source | 74,979 | 43.6% |
| 2-5 | 55,589 | 32.3% |
| 6-10 | 16,317 | 9.5% |
| 11-50 | 19,408 | 11.3% |
| 51-100 | 2,900 | 1.7% |
| 100+ | 2,663 | 1.5% |

Max: 25,065 sources (likely EGFR + lung cancer)

---

## Entrez Mapping Coverage

| Metric | Value |
|--------|-------|
| Before Entrez | 174,965 pairs |
| After Entrez | 171,856 pairs |
| Coverage | 98.2% |
| Lost | 3,109 pairs (1.8%) |

Unmapped genes are mostly non-coding:
- lncRNA: 1,038 (64%)
- Pseudogenes: 361 (22%)
- Protein-coding: 67 (4%)

---

## Running the Pipeline

```bash
# Install dependencies
pip install -r requirements.txt

# Download data
make download-all   # OT data + gene2ensembl + MeSH (~5.5 GB)

# Run pipeline
make pipeline       # Produces gene_disease_mesh_final.tsv

# Or run steps individually
python -m src.pipeline.extract_diseases
python -m src.pipeline.build_crosswalk
python -m src.pipeline.add_entrez
```

---

## File Structure

```
data/processed/
├── gene_disease_mesh_final.tsv     ← PRIMARY OUTPUT (6.1 MB)
├── crosswalks/
│   ├── disease_mesh_crosswalk.csv
│   └── ensembl_entrez.csv
├── intermediate/
│   ├── cancer_diseases_mesh_crosswalk.parquet
│   └── gene_mesh_pre_entrez.parquet
├── summaries/
└── audit/
```

---

## Known Limitations

1. **18.5% MeSH coverage:** Research ontologies (EFO/MONDO) are more granular than clinical vocabulary (MeSH). This is expected, not fixable.

2. **1.8% gene loss:** Ensembl genes without Entrez IDs (mostly lncRNAs/pseudogenes) are dropped.

3. **No time dimension:** OT is a snapshot, not historical. For temporal analysis, use historical OT releases.

4. **Score interpretation:** The 0-1 score combines multiple evidence types. Higher = stronger, but threshold depends on use case.
