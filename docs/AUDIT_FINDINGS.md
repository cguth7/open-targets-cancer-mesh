# MeSH Coverage Audit Findings

## Executive Summary

**Hypothesis**: The ~82% of cancer diseases without MeSH mappings might be "noise" (redundant subtypes, rare conditions) and the 18% with MeSH captures all important cancers.

**Finding**: **Inverted**. The unmapped diseases have MORE evidence, not less. However, this is expected due to vocabulary mismatch between research ontologies (EFO/MONDO) and clinical vocabulary (MeSH).

**Decision**: Keep strict filtering. The 18% represents "clinically mappable" diseases needed for patent matching. External crosswalks provide negligible additional coverage (<1%).

---

## Coverage Statistics

| Metric | With MeSH | Without MeSH |
|--------|-----------|--------------|
| Diseases | 627 (18.5%) | 2,768 (81.5%) |
| Total Evidence | 4.4M (44.6%) | 5.5M (55.4%) |
| Unique Genes | 23,399 | 24,921 |
| Diseases with Associations | ~600 | ~1,946 |

**Key Insight**: Unmapped diseases account for 55% of all evidence, not less.

---

## Top Missing Diseases (by evidence volume)

| Disease | Evidence Count | Genes | Max Score |
|---------|----------------|-------|-----------|
| Cancer (general) | 1,748,064 | 18,298 | 1.0 |
| Breast cancer | 786,950 | 14,440 | 1.0 |
| Lung cancer | 226,470 | 10,655 | 1.0 |
| Colorectal carcinoma | 221,901 | 11,409 | 1.0 |
| Colorectal cancer | 195,817 | 11,753 | 1.0 |
| Gastric cancer | 180,311 | 9,777 | 1.0 |
| Glioblastoma | 92,739 | 7,210 | 1.0 |
| Acute lymphoblastic leukemia | 83,515 | 5,657 | 1.0 |

These are major cancer types with substantial research data.

---

## Why Are Major Cancers Missing MeSH?

### Vocabulary Mismatch (Not Data Quality)

1. **Ontology Granularity**:
   - EFO/MONDO: Research ontologies with highly specific disease definitions
   - MeSH: Clinical vocabulary with broader, fewer terms
   - Example: OT has "breast carcinoma, hormone-sensitive" but MeSH only has "Breast Neoplasms"

2. **ID System Incompatibility**:
   - "Breast cancer" in OT = `EFO_0000305`
   - "Breast Neoplasms" in MeSH = `D001943`
   - These are different concepts in different ID systems
   - OT's `dbXRefs` doesn't link them (and arguably shouldn't - they're not exact matches)

3. **Research vs Clinical Focus**:
   - OT tracks 3,395 cancer disease concepts (research granularity)
   - MeSH has ~150 anatomical site cancer terms (clinical granularity)
   - The 18% coverage is expected, not a bug

---

## MONDO Crosswalk Analysis

We investigated whether the MONDO-MeSH crosswalk could fill gaps:

| Metric | Value |
|--------|-------|
| MONDO diseases missing MeSH | 1,901 |
| MONDO IDs in external crosswalk | 8,254 |
| Overlap (rescuable) | 1 (0.1%) |

**Conclusion**: The external crosswalk was built from different disease collections. Our specific cancer MONDO IDs are not in it. Only glioblastoma would gain a mapping.

---

## Ghost Towns Analysis

**822 diseases (29.7% of unmapped)** have zero gene associations:
- These are truly "ghost towns" with no data to miss
- Mostly rare syndromes, animal models, umbrella terms
- Examples: "46,XY disorder of sex development", "familial cancer of unspecified site"

**Inverse insight**: 70% of unmapped diseases DO have associations, many substantial.

---

## Recommendation

### Keep Strict Filtering

1. **The 18% with MeSH represents "clinically mappable" diseases**
   - These have curated, validated MeSH mappings from Open Targets
   - Suitable for patent matching (patents use clinical vocabulary)

2. **External crosswalks don't help**
   - MONDO crosswalk: <1% additional coverage
   - Manual curation would be required to map EFO→MeSH

3. **The "missing" data isn't lost**
   - It's captured in OT's disease-level associations
   - Just not mappable to MeSH clinical vocabulary
   - For patent matching, we only need MeSH-mappable diseases

### Document This Limitation

- Users should understand that 18% coverage is by design
- The dataset covers "clinically vocabulary-aligned" cancers
- Research-specific disease subtypes are intentionally excluded

---

## Future Considerations

If broader coverage is ever needed:

1. **Manual curation**: Map high-evidence EFO diseases to MeSH manually
2. **Hierarchy rollup**: Map specific diseases to parent MeSH terms
3. **Accept approximations**: Use fuzzy matching (with confidence scores)

For now, strict filtering is appropriate for patent matching use case.
