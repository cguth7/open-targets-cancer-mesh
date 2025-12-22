# Open Targets Cancer Data Pipeline
## Status Report & Decision Points

**Date:** December 2024
**Status:** Phase 2 Complete - Edge lists built, MeSH crosswalk in place

---

## Project Purpose

**Goal:** Connect Open Targets gene-disease associations to pharma/patent success data to analyze how clinical drug failures affect drug development for other cancer drugs.

**Pipeline:** Open Targets → MeSH + EntrezGene crosswalk → Link to patent/trial databases

---

## Executive Summary

We are building an edge list of gene-disease associations from Open Targets Platform, restricted to cancer, with crosswalks to standard identifiers (MeSH for diseases, EntrezGene for genes).

**Current state:** Phase 2 complete. Built edge lists with 627 diseases having direct MeSH mappings from Open Targets. Discovered that OT provides 586 unique MeSH IDs, but our reference hierarchy only covers 91 of them.

**Key finding:** MeSH has parallel hierarchies ("by site" AND "by histologic type"). A single cancer can have multiple tree paths. Open Targets captures this - 13 diseases have multiple MeSH IDs.

---

## Data Overview

### What Open Targets Provides
Open Targets Platform aggregates evidence linking **genes (targets)** to **diseases** from multiple sources (GWAS, clinical trials, literature, etc.). Each gene-disease pair has an **association score** (0-1) reflecting strength of evidence.

### Data Structure
```
Association = (Gene, Disease, Score)

Example:
  Gene:    ENSG00000141510 (TP53)
  Disease: EFO_0000311 (lung cancer)
  Score:   0.85
```

### What We Downloaded (Phase 1)
| Dataset | Records | Size | Description |
|---------|---------|------|-------------|
| Disease index | 46,960 | ~6MB | All diseases with ontology, crossrefs |
| Target index | 78,725 | ~78MB | All genes with symbols, crossrefs |

### What Remains (Phase 2)
| Dataset | Est. Size | Description |
|---------|-----------|-------------|
| Indirect associations | ~3-4GB | Comprehensive (includes inherited links) |
| Direct associations | ~2-3GB | Strict (explicit evidence only) |

---

## Key Findings

### 1. Identifier Systems Differ

| Data Type | Open Targets Uses | We Need |
|-----------|-------------------|---------|
| Diseases | EFO / MONDO / Orphanet | MeSH |
| Genes | Ensembl (ENSG...) | EntrezGene (numeric) |

**Implication:** We must build crosswalks for both diseases and genes.

### 2. Granularity Mismatch (Diseases)

| Source | Cancer Terms | Granularity |
|--------|--------------|-------------|
| MeSH (Level 5+) | ~44 | Organ-level (Lung, Breast, Prostate...) |
| Open Targets | 3,395 | Subtype-level (adenocarcinoma variants, etc.) |

**Example:** "Lung Neoplasms" (MeSH D008175) maps to 83 different Open Targets diseases.

**Implication:** Many-to-one mapping required. Decision needed on how to handle.

### 3. MeSH Coverage in Open Targets is Low (but usable)

Only **627 of 3,395 (18.5%)** Open Targets cancer diseases have MeSH IDs in their cross-reference fields.

However, these 627 diseases provide **586 unique MeSH IDs** - more than enough for pharma/patent matching.

**Implication:** For exact matching to patent data, use the OT-provided MeSH IDs directly. For aggregation by site/histology, need hierarchy lookups.

### 3a. MeSH Parallel Hierarchies (Important!)

MeSH C04 (Neoplasms) has **two major classification systems**:
- **C04.588** = "By Site" (lung, breast, colon...)
- **C04.557** = "By Histologic Type" (adenocarcinoma, leukemia, lymphoma...)

**A single cancer can appear in BOTH hierarchies.** Example:
- "Adenocarcinoma of Lung" (D000077192) has TWO tree paths:
  - `C04.557.470.200.025.022` → By Histologic Type → Glandular/Epithelial
  - `C04.588.894.797.520.055` → By Site → Thoracic → Lung

**Open Targets captures this:** 13 diseases in our crosswalk have multiple MeSH IDs.

### 3b. Reference Hierarchy Gap

| Metric | Count |
|--------|-------|
| Unique MeSH IDs from OT | 586 |
| In our reference file (levels 1-7) | 91 |
| NOT in reference | 495 |

The 495 "missing" are:
- **405 D-codes** at deeper levels (our reference stops at level 7, MeSH goes to 10+)
- **89 C-codes** (supplementary concepts, not in main hierarchy)
- **1 other**

**Implication:** Our reference file is good for understanding hierarchy structure, but OT diseases map to much more specific MeSH terms than we catalogued.

### 4. Open Targets "Cancer" Definition Includes Edge Cases

We filtered diseases by having "neoplasm" (EFO_0000616) in their ontology ancestors:
- **91% (3,094)** have clear cancer keywords (carcinoma, tumor, sarcoma, etc.)
- **9% (301)** are ambiguous:
  - Cancer predisposition syndromes (Lynch, MEN1) - related but not cancers
  - Possible ontology errors (some infectious/inflammatory conditions)

**Implication:** Decision needed on filtering strictness.

### 5. Gene ID Crosswalk Not Available in Open Targets

Open Targets provides Ensembl gene IDs but not EntrezGene. The target dataset has 78,725 genes.

**Options:**
- Download NCBI gene2ensembl file (~300MB compressed)
- Use gene symbols as bridge (less reliable)
- Determine actual gene count in cancer associations first (may be smaller subset)

---

## Decisions Needed

### Decision 1: Association Type

Open Targets provides two versions of association scores:

| Type | Description | Use Case |
|------|-------------|----------|
| **Indirect** | Includes inherited associations from disease hierarchy | More comprehensive; matches OT website UI |
| **Direct** | Only explicit evidence links | Stricter; conservative analysis |

**Example:** If gene X has evidence for "breast ductal carcinoma", the indirect version also shows association with parent term "breast cancer". Direct version only shows the specific subtype.

**Recommendation:** Indirect (more comprehensive, standard choice)

**Question:** Do you want indirect only, direct only, or both?

---

### Decision 2: MeSH Granularity Level

The MeSH neoplasm hierarchy (C04) has multiple levels:

| Level | Count | Examples | Notes |
|-------|-------|----------|-------|
| 3 | 31 | Breast Neoplasms, Leukemia, Lymphoma | Organ systems |
| 4 | 53 | Liver, Pancreatic, Leukemia Myeloid | Organ groups |
| 5 | 37 | Lung, Prostate, Ovarian, AML | **Specific organs** |
| 6 | 5 | Colorectal, Colonic, Rectal | Sub-organ |

**Note:** Common cancers (lung, prostate, colorectal) are at Level 5-6, not Level 4.

**Question:** Which level(s) should we target? Level 4+5 combined gives ~90 terms.

---

### Decision 3: OT → MeSH Mapping Strategy

**Option A: Many-to-One Rollup**
- Aggregate all OT subtypes to their MeSH parent category
- Output: One row per (Gene, MeSH Cancer) pair with aggregated score
- Pros: Clean, matches MeSH granularity
- Cons: Loses subtype detail

**Option B: Preserve Granularity**
- Keep all 3,395 OT diseases, add MeSH parent as additional column
- Output: One row per (Gene, OT Disease) pair, with MeSH category annotation
- Pros: Full detail preserved, can aggregate downstream
- Cons: Larger output, more complex

**Option C: High-Confidence Only**
- Use only the 627 OT diseases with existing MeSH crossrefs
- Pros: No ambiguous mappings
- Cons: Loses 82% of data

**Recommendation:** Option B (preserve granularity, aggregate later if needed)

---

### Decision 4: Handling Ambiguous Cancer Entries

301 Open Targets diseases lack obvious cancer keywords. These include:
- Cancer predisposition syndromes (Lynch syndrome, MEN1)
- Precancerous conditions
- Possible ontology errors

**Options:**
- **Strict filter:** Require cancer keywords → drops 301 entries
- **Manual curation:** Review 301 entries individually
- **Keep all:** Trust ontology, accept some noise

**Recommendation:** Strict filter for main dataset; separate file for syndromes if desired

---

### Decision 5: EntrezGene Crosswalk

**Options:**
- **Download NCBI file:** gene2ensembl (~300MB) - comprehensive
- **Gene symbols:** Use HGNC symbols as bridge - faster but less reliable
- **Defer:** Deliver with Ensembl IDs; add EntrezGene later

**Recommendation:** Download NCBI file (one-time cost, reliable)

---

## Proposed Output Schema

```
| Column | Type | Description |
|--------|------|-------------|
| diseaseId | string | Open Targets disease ID (EFO/MONDO) |
| diseaseName | string | Human-readable disease name |
| meshId | string | MeSH descriptor ID (e.g., D008175) |
| meshName | string | MeSH term name (e.g., Lung Neoplasms) |
| meshLevel | int | MeSH tree level (3-7) |
| targetId | string | Ensembl gene ID |
| entrezGeneId | string | NCBI EntrezGene ID |
| geneSymbol | string | HGNC gene symbol |
| score | float | Association score (0-1) |
```

---

## Next Steps (After Decisions)

1. Finalize MeSH target level and mapping strategy
2. Build OT disease → MeSH crosswalk (keyword-based + manual review)
3. Download NCBI gene2ensembl for gene crosswalk
4. Download Phase 2 associations (~3-5GB)
5. Build and validate final edge list
6. Output as Parquet + CSV

---

## Repository Structure

```
open_targets/
├── data/
│   ├── opentargets/      # Raw OT data
│   ├── mesh/             # MeSH reference files
│   └── processed/        # Pipeline outputs
├── docs/
│   ├── MESH_CANCER_LEVELS_SUMMARY.md    # MeSH hierarchy breakdown
│   └── CROSSWALK_REFERENCE_LISTS.md     # Full lists for review
├── scripts/
│   ├── download_phase1.sh
│   ├── download_phase2.sh
│   ├── explore_data.py
│   ├── build_edge_list.py
│   └── gen_crosswalk_md.py
├── LEARNINGS.md              # This document
├── MESH_OT_MAPPING_ANALYSIS.md  # Detailed mapping methodology
└── requirements.txt
```

---

## Reference Files

- `docs/MESH_CANCER_LEVELS_SUMMARY.md` - Detailed MeSH hierarchy breakdown
- `docs/CROSSWALK_REFERENCE_LISTS.md` - Full list of MeSH terms and OT diseases for review
- `data/mesh/mesh_neoplasms_all_levels.csv` - MeSH terms as structured data (levels 1-7 only)
