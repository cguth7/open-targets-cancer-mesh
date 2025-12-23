# Data Quality Issue: Mechanical/Computed Associations in Open Targets

## Summary

**22.7% of Open Targets direct associations** appear to be mechanical/computed rather than literature-derived. These have fixed score values and single evidence counts, suggesting automated inference rather than paper-based curation.

## Data Source

- **File**: `data/opentargets/association_overall_direct/*.parquet`
- **Type**: "Direct" associations (gene directly associated with disease)
- **Platform version**: Open Targets v25.12

## Finding: Systematic Low-Score Associations

**Total direct associations**: 4,492,971

### Suspicious Fixed-Value Scores

| Score | Associations | % of Total |
|-------|-------------|------------|
| 0.001478 | 372,461 | 8.3% |
| 0.003696 | 240,157 | 5.3% |
| 0.002217 | 235,290 | 5.2% |
| 0.002957 | 62,646 | 1.4% |
| 0.005914 | 14,300 | 0.3% |
| 0.007392 | 95,041 | 2.1% |
| **TOTAL** | **1,019,895** | **22.7%** |

### Evidence Count Analysis

- Associations with score < 0.01: **1,829,065** (40.7%)
- Of these, evidence_count = 1: **1,223,047** (66.9%)

### Score Distribution

| Threshold | Count | % of Total |
|-----------|-------|------------|
| < 0.01 | 1,829,065 | 40.7% |
| < 0.05 | 3,301,673 | 73.5% |
| < 0.10 | 3,771,256 | 83.9% |
| >= 0.10 | 721,715 | 16.1% |

## Interpretation

These fixed-value scores appear to be **NOT from literature/papers**:

1. **Score quantization**: Real paper-based scores would have continuous distributions, not exact repeated values across 200K+ associations

2. **Likely sources**:
   - Expression Atlas (differential expression in cancer vs normal)
   - Text-mining with fixed confidence thresholds
   - Other automated computational pipelines

3. **Single evidence**: All have `evidenceCount = 1`, meaning a single data source contributed

4. **Pattern suggests automation**: Scores are bucketed at specific thresholds, indicating automated classification rather than continuous evidence-based scoring

## Impact on Final Dataset

**Final gene_disease_mesh_final.tsv**: 171,856 rows

| Score Range | Rows | % |
|-------------|------|---|
| < 0.01 | 90,784 | 52.8% |
| < 0.05 | 135,975 | 79.1% |
| < 0.10 | 154,601 | 90.0% |
| >= 0.10 | 17,255 | 10.0% |

### High Entrez ID Genes (>= 200,000)

These are predominantly lncRNAs, miRNAs, and pseudogenes:

- Rows: 12,669 (7.4%)
- Mean score: 0.0301
- Score < 0.05: 83.8%
- Evidence = 1: 55.7%

## Visual Evidence

In the 120x120 gene-disease grid (`data/processed/figures/rankings/top120_gene_disease_grid.png`), genes with Entrez ID >= 200,000 show **suspicious banding patterns** - nearly identical association profiles across many genes, consistent with mechanical assignment rather than biological signal.

## Finding: Cloned Gene Association Patterns

A second anomaly was discovered: **8 genes with essentially identical association data**.

### Affected Genes (Entrez IDs)

| Entrez ID | Position in Top 120 |
|-----------|---------------------|
| 203068 | 85 |
| 84617 | 86 |
| 10382 | 87 |
| 10383 | 88 |
| 347733 | 89 |
| 7280 | 90 |
| 81027 | 91 |
| 347688 | 92 |

### Evidence of Cloning

These 8 genes have:

1. **100% disease overlap** - All associated with the exact same 56 diseases
2. **Nearly identical scores** - Top disease scores within 0.01 of each other:
   - D002289 (NSCLC): 0.6060 - 0.6185
   - D011471 (Prostate): 0.5911 - 0.5936
   - D001943 (Breast): 0.5926 - 0.5945
3. **Nearly identical evidence counts** - NSCLC evidence: 1262-1295 (within 2.6%)
4. **Correlation = 1.0** between adjacent genes in this band

### Why This Is Suspicious

Even closely related gene family members should NOT have:
- Identical disease associations
- Scores within 1% of each other
- Evidence counts within 3% of each other

This pattern suggests either:
1. Data was copied/duplicated during processing
2. These genes were assigned scores from a shared source without differentiation
3. A systematic error in the Open Targets pipeline

### Impact

These genes appear in the **top 100 by evidence**, inflating apparent gene diversity in cancer associations.

## Recommendation

Users of this dataset should consider filtering:

```python
# High-confidence only
df = df[df['ot_score'] >= 0.1]  # Keeps ~10% of rows

# Multiple evidence sources
df = df[df['evidence_count'] >= 2]

# Exclude computational gene IDs
df = df[df['gene_entrez_id'] < 200000]
```

## Questions for Open Targets

1. Which data sources contribute these fixed-score associations?
2. Are these from Expression Atlas differential expression analysis?
3. What is the scoring methodology that produces these quantized values?
4. Should these be flagged differently in the platform?
