import pandas as pd

mesh = pd.read_csv('output/mesh_neoplasms_all_levels.csv')
ot = pd.read_parquet('output/cancer_diseases_mesh_crosswalk.parquet')

md = """# Cancer Crosswalk Reference Lists

## Part 1: MeSH Neoplasm Terms (144 total)

### Level 3: Organ Systems (31 terms)
| MeSH ID | Name |
|---------|------|
"""

for _, row in mesh[mesh['level'] == 3].sort_values('mesh_name').iterrows():
    md += f"| {row['mesh_id']} | {row['mesh_name']} |\n"

md += """
### Level 4: Organ Groups (53 terms)
| MeSH ID | Name |
|---------|------|
"""

for _, row in mesh[mesh['level'] == 4].sort_values('mesh_name').iterrows():
    md += f"| {row['mesh_id']} | {row['mesh_name']} |\n"

md += """
### Level 5+: Specific Organs (44 terms) - KEY LEVEL
| MeSH ID | Name | Level |
|---------|------|-------|
"""

for _, row in mesh[mesh['level'] >= 5].sort_values('mesh_name').iterrows():
    md += f"| {row['mesh_id']} | {row['mesh_name']} | {row['level']} |\n"

md += """

---

## Part 2: Open Targets Cancer Diseases (3,395 total)

Sorted alphabetically. Format: `EFO/MONDO ID: Disease Name`

"""

# Group by first letter for easier reading
ot_sorted = ot.sort_values('diseaseName')
current_letter = ''
for _, row in ot_sorted.iterrows():
    name = str(row['diseaseName'])
    if not name or name == 'nan':
        continue
    first = name[0].upper()
    if first != current_letter and first.isalpha():
        current_letter = first
        md += f"\n### {first}\n"
    md += f"- {row['diseaseId']}: {name}\n"

with open('output/CROSSWALK_REFERENCE_LISTS.md', 'w') as f:
    f.write(md)

print(f"Written to output/CROSSWALK_REFERENCE_LISTS.md")
print(f"MeSH terms: {len(mesh)}")
print(f"OT diseases: {len(ot)}")
