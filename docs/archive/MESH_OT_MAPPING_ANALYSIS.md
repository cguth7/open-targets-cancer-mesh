# MeSH ↔ Open Targets Cancer Mapping Analysis

## Executive Summary

| Metric | Value |
|--------|-------|
| Total OT cancer diseases | 3,395 |
| With direct MeSH IDs from OT | 627 (18.5%) |
| Unique MeSH IDs from OT | 586 |
| Matched to MeSH (keyword-based) | 2,634 (77.6%) |
| Unmatched | 761 (22.4%) |

## Critical Finding: Parallel Hierarchies

**MeSH C04 has two classification systems that overlap:**
- **C04.588** = "Neoplasms by Site" (anatomical location)
- **C04.557** = "Neoplasms by Histologic Type" (cell/tissue type)

**Confirmed examples from MeSH API:**

| MeSH ID | Term | Tree Paths |
|---------|------|------------|
| D000077192 | Adenocarcinoma of Lung | `C04.557.470.200.025.022` (histologic) AND `C04.588.894.797.520.055` (site) |
| D000236 | Adenoma | `C04.557.470.035` (histologic only) |

**Open Targets captures this:** 13 diseases in our data have multiple MeSH IDs, including:
- lung adenocarcinoma → D000077192, C538231
- head/neck squamous cell carcinoma → D000077195, C535575
- nasopharyngeal carcinoma → D000077274, D00007727, C538339

## Reference Hierarchy Gap

Our `mesh_neoplasms_all_levels.csv` only covers levels 1-7:

| Metric | Count |
|--------|-------|
| MeSH IDs from Open Targets | 586 |
| In our reference file | 91 (15.5%) |
| NOT in our reference | 495 (84.5%) |

**What's missing:**
- 405 D-codes at deeper levels (level 8-10+)
- 89 C-codes (supplementary concepts)

**Implication for pharma matching:** Use OT's MeSH IDs directly for exact matching. Our reference is useful for understanding hierarchy structure but incomplete for full coverage.

---

## Matching Methodology

### Approach: Exact Substring Matching (Case-Insensitive)

We use **simple substring matching**, NOT fuzzy matching. For each MeSH term, we define a list of keywords. An Open Targets disease matches if **ANY keyword appears as a substring** in the disease name.

```python
# Example: How matching works
mesh_term = "D008175 - Lung Neoplasms"
keywords = ['lung', 'pulmonary', 'bronch', 'bronchogenic']

# For each OT disease name (lowercased):
#   if any(keyword in disease_name for keyword in keywords):
#       → MATCH

# "lung adenocarcinoma" → MATCH (contains 'lung')
# "pulmonary blastoma" → MATCH (contains 'pulmonary')
# "bronchioloalveolar carcinoma" → MATCH (contains 'bronch')
# "small cell carcinoma" → NO MATCH (no keyword present)
```

### Why NOT Fuzzy Matching?

1. **Precision over recall** - Substring matching avoids false positives
2. **Interpretable** - Easy to understand why something matched
3. **Controllable** - Can add specific keywords as needed
4. **Fast** - No external libraries needed

### Limitations

- Misses synonyms not in keyword list (e.g., "pneumonic" for lung)
- Misses abbreviations (e.g., "NSCLC" for non-small cell lung cancer)
- Misses alternate spellings (e.g., "oesophageal" vs "esophageal" - we include both)

---

## Keyword Definitions (Current)

### Level 5 - Specific Organs (The ~60 Key Cancers)

| MeSH ID | MeSH Name | Keywords Used |
|---------|-----------|---------------|
| D008175 | Lung Neoplasms | `lung`, `pulmonary`, `bronch`, `bronchogenic` |
| D015179 | Colorectal Neoplasms | `colorectal`, `colon`, `rectal`, `rectum` |
| D001943 | Breast Neoplasms | `breast`, `mammary` |
| D011471 | Prostatic Neoplasms | `prostate`, `prostatic` |
| D010051 | Ovarian Neoplasms | `ovarian`, `ovary` |
| D007680 | Kidney Neoplasms | `kidney`, `renal`, `nephroblastoma`, `wilms` |
| D001749 | Urinary Bladder Neoplasms | `bladder`, `urothelial` |
| D013274 | Stomach Neoplasms | `stomach`, `gastric` |
| D014594 | Uterine Neoplasms | `uterine`, `uterus`, `endometrial`, `myometri` |
| D013736 | Testicular Neoplasms | `testicular`, `testis` |

### Level 4 - Organ Groups

| MeSH ID | MeSH Name | Keywords Used |
|---------|-----------|---------------|
| D005770 | Gastrointestinal Neoplasms | `gastrointestinal`, `stomach`, `gastric`, `intestin`, `colon`, `rectal`, `colorectal`, `esophag`, `oesophag`, `appendix`, `duoden`, `jejun`, `ileal`, `ileum`, `cecal`, `cecum`, `anal`, `anus`, `ampulla of vater`, `cardia` |
| D008113 | Liver Neoplasms | `liver`, `hepat`, `hepatocellular`, `hepatoblastoma`, `bile duct`, `biliary`, `cholangiocarcinoma`, `gallbladder` |
| D012142 | Respiratory Tract Neoplasms | `respiratory`, `lung`, `pulmonary`, `bronch`, `trachea`, `pleura`, `mesothel`, `nasopharyn`, `laryn`, `nasal`, `sinus` |
| D005833 | Genital Neoplasms, Female | `ovarian`, `ovary`, `uterine`, `uterus`, `cervical`, `cervix`, `endometrial`, `fallopian`, `vaginal`, `vulvar`, `vulva`, `female genital`, `female reproductive` |
| D005834 | Genital Neoplasms, Male | `prostate`, `prostatic`, `testicular`, `testis`, `penile`, `penis`, `male genital`, `male reproductive`, `epididym`, `seminal vesicle`, `spermatic cord` |
| D014571 | Urologic Neoplasms | `urologic`, `kidney`, `renal`, `bladder`, `ureter`, `urethral`, `urinary`, `nephroblastoma`, `wilms` |

### Level 3 - Organ Systems & Histologic Types

| MeSH ID | MeSH Name | Keywords Used |
|---------|-----------|---------------|
| D007938 | Leukemia | `leukemia`, `leukaemia` |
| D008223 | Lymphoma | `lymphoma`, `lymphoproliferative` |
| D009380 | Nervous System Neoplasms | `nervous system`, `brain`, `cns`, `neural`, `cerebr`, `glioma`, `glioblastoma`, `neuroblastoma`, `meningioma`, `astrocyt`, `schwannoma`, `neurofibroma`, `spinal cord` |
| D012983 | Soft Tissue Neoplasms | `soft tissue`, `sarcoma`, `leiomyo`, `rhabdomyo`, `liposarcoma`, `fibrosarcoma`, `angiosarcoma`, `lipoma`, `fibroma`, `myxoma`, `hemangioma`, `angioma` |
| D008545 | Melanoma | `melanoma`, `nevus`, `nevi` |

---

## Matching Examples (Detailed)

### Example 1: Lung Neoplasms (D008175)

**Keywords:** `lung`, `pulmonary`, `bronch`, `bronchogenic`

| OT Disease Name | Matched Keyword | Result |
|-----------------|-----------------|--------|
| lung adenocarcinoma | `lung` | ✓ MATCH |
| pulmonary blastoma | `pulmonary` | ✓ MATCH |
| bronchus mucoepidermoid carcinoma | `bronch` | ✓ MATCH |
| mucinous bronchioloalveolar adenocarcinoma | `bronch` | ✓ MATCH |
| non-small cell carcinoma | (none) | ✗ NO MATCH |
| small cell carcinoma | (none) | ✗ NO MATCH |

**Note:** "non-small cell carcinoma" and "small cell carcinoma" don't match because they lack organ-specific keywords. They would need "lung" prefix to match (e.g., "small cell lung carcinoma").

### Example 2: Colorectal Neoplasms (D015179)

**Keywords:** `colorectal`, `colon`, `rectal`, `rectum`

| OT Disease Name | Matched Keyword | Result |
|-----------------|-----------------|--------|
| colon adenocarcinoma | `colon` | ✓ MATCH |
| rectal squamous cell carcinoma | `rectal` | ✓ MATCH |
| sigmoid colon cancer | `colon` | ✓ MATCH |
| colorectal cancer | `colorectal` | ✓ MATCH |
| colonic lymphangioma | `colon` | ✓ MATCH |
| bowel cancer | (none) | ✗ NO MATCH |

**Note:** "bowel cancer" doesn't match - would need to add `bowel` keyword.

### Example 3: Breast Neoplasms (D001943)

**Keywords:** `breast`, `mammary`

| OT Disease Name | Matched Keyword | Result |
|-----------------|-----------------|--------|
| breast adenocarcinoma | `breast` | ✓ MATCH |
| triple-negative breast cancer | `breast` | ✓ MATCH |
| mammary Paget disease | `mammary` | ✓ MATCH |
| intraductal papillary breast neoplasm | `breast` | ✓ MATCH |
| ductal carcinoma in situ | (none) | ✗ NO MATCH |

**Note:** "ductal carcinoma in situ" (DCIS) doesn't match because it lacks "breast" - the full name would be "breast ductal carcinoma in situ".

---

## Coverage by MeSH Term (Top 30)

| MeSH ID | Level | OT Count | MeSH Name |
|---------|-------|----------|-----------|
| D012983 | 3 | 416 | Soft Tissue Neoplasms |
| D009375 | 3 | 395 | Neoplasms, Glandular and Epithelial |
| D005833 | 4 | 306 | Genital Neoplasms, Female |
| D018204 | 3 | 280 | Neoplasms, Connective and Soft Tissue |
| D005770 | 4 | 274 | Gastrointestinal Neoplasms |
| D009380 | 3 | 272 | Nervous System Neoplasms |
| D014571 | 4 | 207 | Urologic Neoplasms |
| D012142 | 4 | 195 | Respiratory Tract Neoplasms |
| D004701 | 3 | 176 | Endocrine Gland Neoplasms |
| D007938 | 3 | 139 | Leukemia |
| D012878 | 3 | 132 | Skin Neoplasms |
| D009373 | 3 | 128 | Neoplasms, Germ Cell and Embryonal |
| D008223 | 3 | 126 | Lymphoma |
| D008113 | 4 | 122 | Liver Neoplasms |
| D010051 | 5 | 114 | Ovarian Neoplasms |
| D007680 | 5 | 106 | Kidney Neoplasms |
| D005834 | 4 | 103 | Genital Neoplasms, Male |
| D001943 | 3 | 100 | Breast Neoplasms |
| D015179 | 6 | 98 | Colorectal Neoplasms |
| D001859 | 3 | 97 | Bone Neoplasms |
| D001749 | 5 | 84 | Urinary Bladder Neoplasms |
| D008175 | 5 | 83 | Lung Neoplasms |
| D008545 | 4 | 80 | Melanoma |
| D009062 | 4 | 73 | Mouth Neoplasms |
| D013964 | 4 | 69 | Thyroid Neoplasms |
| D014594 | 5 | 63 | Uterine Neoplasms |
| D006258 | 3 | 63 | Head and Neck Neoplasms |
| D005134 | 3 | 49 | Eye Neoplasms |
| D010190 | 4 | 49 | Pancreatic Neoplasms |
| D013274 | 5 | 48 | Stomach Neoplasms |

---

## Unmatched Diseases Analysis (761 total, 22.4%)

### Category 1: Generic System-Level Terms (~150)

These diseases name a body system but no specific organ. No MeSH term exists at this level.

| OT Disease | Why No Match |
|------------|--------------|
| lymphatic system cancer | No keyword for "lymphatic system" - too generic |
| immune system cancer | No keyword for "immune system" - too generic |
| musculoskeletal system cancer | No keyword for "musculoskeletal" |
| reproductive system cancer | No keyword for "reproductive system" |
| cardiovascular cancer | No keyword for "cardiovascular" |
| sensory system cancer | No keyword for "sensory" |

**Recommendation:** These are umbrella terms. Could map to multiple MeSH terms or exclude.

### Category 2: Benign Neoplasms (~200)

Many benign tumors are named generically without organ specification.

| OT Disease | Why No Match |
|------------|--------------|
| benign digestive system neoplasm | "digestive system" not specific enough |
| cardiovascular organ benign neoplasm | "cardiovascular" not in keywords |
| immune system organ benign neoplasm | "immune system" not in keywords |
| thoracic benign neoplasm | "thoracic" matches but it's generic |
| peritoneal benign neoplasm | "peritoneal" not in keywords |

**Recommendation:** Add "benign" variants if benign tumors are in scope.

### Category 3: Rare Anatomical Locations (~100)

Specific anatomical sites not covered by current keywords.

| OT Disease | Missing Keyword |
|------------|-----------------|
| sublingual gland adenoid cystic carcinoma | `sublingual` |
| broad ligament malignant neoplasm | `broad ligament` |
| urachus cancer | `urachus` |
| lacrimal duct cancer | `lacrimal` |
| pericardium cancer | `pericardium` |
| heart cancer | `heart`, `cardiac` |
| round ligament tumor | `round ligament` |

**Recommendation:** Add keywords for common rare sites, or accept lower coverage.

### Category 4: Non-Cancer Conditions (~50)

These appear to be ontology errors - conditions that have "neoplasm" in their ancestry but aren't actually cancers.

| OT Disease | Why It's Not Cancer |
|------------|---------------------|
| tuberculous salpingitis | Infection, not cancer |
| tuberculous epididymitis | Infection, not cancer |
| arteriovenous malformations of the brain | Vascular malformation |
| postinflammatory pulmonary fibrosis | Fibrotic condition |

**Recommendation:** Exclude these using a blocklist.

### Category 5: Cancer Syndromes (~40)

Hereditary conditions that predispose to cancer, but aren't cancers themselves.

| OT Disease | Notes |
|------------|-------|
| Lynch syndrome | Hereditary colorectal cancer syndrome |
| Muir-Torre syndrome | Variant of Lynch syndrome |
| Li-Fraumeni syndrome | TP53 mutation syndrome |
| rhabdoid tumor predisposition syndrome | SMARCB1 mutation |
| multiple endocrine neoplasia type 1 | MEN1 mutation |

**Recommendation:** Keep in separate "syndromes" file if relevant to analysis.

### Category 6: Unusual Cell Type Naming (~100)

Named by cell type rather than organ.

| OT Disease | Notes |
|------------|-------|
| malignant Leydig cell tumor | Testicular - could add `leydig` |
| Sertoli cell tumor | Testicular - could add `sertoli` |
| granulosa cell tumor | Ovarian - could add `granulosa` |
| giant cell tumor | Generic - no specific organ |
| chromaffin cell tumor | Adrenal - could add `chromaffin` |

**Recommendation:** Add cell-type keywords for common patterns.

---

## One-to-Many Relationships

### Many OT → One MeSH (Expected)

This is the normal case. Example for Lung Neoplasms (D008175):

```
D008175 (Lung Neoplasms)
├── lung adenocarcinoma
├── lung squamous cell carcinoma
├── small cell lung carcinoma
├── large cell lung carcinoma
├── lung adenosquamous carcinoma
├── pulmonary blastoma
├── bronchioloalveolar carcinoma
├── ... (83 total OT diseases)
```

### One OT → Many MeSH (Also Common)

~1,300 OT diseases map to multiple MeSH terms because:
1. MeSH has parallel hierarchies ("by site" AND "by histologic type")
2. Some cancers span multiple organs

Example:
```
"ovarian adenocarcinoma" maps to:
├── D010051 (Ovarian Neoplasms) - by site
└── D009375 (Neoplasms, Glandular and Epithelial) - by histology
```

---

## Recommendations

1. **For ~60 specific cancers:** Use Level 5 MeSH terms with current keywords - 77% coverage is reasonable

2. **To improve coverage:**
   - Add ~20 missing keywords for rare anatomical sites
   - Add cell-type keywords (Leydig, Sertoli, granulosa)
   - Could reach ~85% coverage

3. **Exclude:**
   - Non-cancer conditions (tuberculosis, AV malformations)
   - Generic system-level terms (or map to multiple MeSH)

4. **Handle separately:**
   - Cancer syndromes (Lynch, Li-Fraumeni, etc.)
   - Benign neoplasms (if not in scope)

---

## Files

- `data/mesh/mesh_neoplasms_all_levels.csv` - MeSH hierarchy (144 terms)
- `data/processed/cancer_diseases_mesh_crosswalk.parquet` - OT cancer diseases (3,395)
- `CROSSWALK_REFERENCE_LISTS.md` - Full lists for manual review
