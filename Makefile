# Open Targets Cancer MeSH Pipeline
# Reproducible pipeline for building gene-disease-MeSH datasets

.PHONY: all clean download-phase1 download-phase2 download-entrez pipeline audit help

# Configuration
PYTHON := python3
DATA_DIR := data
OT_DIR := $(DATA_DIR)/opentargets
NCBI_DIR := $(DATA_DIR)/ncbi
PROCESSED_DIR := $(DATA_DIR)/processed

# Open Targets FTP (v25.12)
OT_FTP := ftp.ebi.ac.uk::pub/databases/opentargets/platform/25.12/output/etl/parquet

# NCBI gene2ensembl
GENE2ENSEMBL_URL := https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz

# Default target
all: pipeline

help:
	@echo "Open Targets Cancer MeSH Pipeline"
	@echo ""
	@echo "Usage:"
	@echo "  make download-phase1   Download disease & target indexes (~75 MB)"
	@echo "  make download-phase2   Download association data (~5 GB)"
	@echo "  make download-entrez   Download NCBI gene2ensembl (~278 MB)"
	@echo "  make download-all      Download all required data"
	@echo "  make pipeline          Run the complete pipeline"
	@echo "  make audit             Run MeSH coverage audit"
	@echo "  make clean             Remove processed outputs"
	@echo "  make clean-all         Remove all data (including downloads)"
	@echo ""
	@echo "Quick start:"
	@echo "  make download-all && make pipeline"

# =============================================================================
# DATA DOWNLOADS
# =============================================================================

download-phase1: $(OT_DIR)/disease $(OT_DIR)/target

$(OT_DIR)/disease:
	@echo "Downloading Open Targets disease index..."
	@mkdir -p $(OT_DIR)
	rsync -rpltvz --delete $(OT_FTP)/diseases/ $(OT_DIR)/disease/

$(OT_DIR)/target:
	@echo "Downloading Open Targets target index..."
	@mkdir -p $(OT_DIR)
	rsync -rpltvz --delete $(OT_FTP)/targets/ $(OT_DIR)/target/

download-phase2: $(OT_DIR)/association_overall_direct

$(OT_DIR)/association_overall_direct:
	@echo "Downloading Open Targets associations (this may take a while)..."
	@mkdir -p $(OT_DIR)
	rsync -rpltvz --delete $(OT_FTP)/associationByOverallDirect/ $(OT_DIR)/association_overall_direct/

download-entrez: $(NCBI_DIR)/gene2ensembl.gz

$(NCBI_DIR)/gene2ensembl.gz:
	@echo "Downloading NCBI gene2ensembl (~278 MB)..."
	@mkdir -p $(NCBI_DIR)
	curl -o $(NCBI_DIR)/gene2ensembl.gz $(GENE2ENSEMBL_URL)

download-all: download-phase1 download-phase2 download-entrez

# =============================================================================
# PIPELINE
# =============================================================================

pipeline: $(PROCESSED_DIR)/cancer_gene_mesh_site_only_with_entrez.parquet

# Step 1: Extract cancer diseases
$(PROCESSED_DIR)/cancer_diseases_mesh_crosswalk.parquet: $(OT_DIR)/disease
	@echo "Step 1: Extracting cancer diseases..."
	$(PYTHON) -m src.pipeline.extract_diseases

# Step 2: Build crosswalk
$(PROCESSED_DIR)/cancer_gene_disease_mesh_site_only.parquet: $(PROCESSED_DIR)/cancer_diseases_mesh_crosswalk.parquet $(OT_DIR)/association_overall_direct $(DATA_DIR)/mesh/mesh_c04_complete.csv
	@echo "Step 2: Building gene-disease-MeSH crosswalk..."
	$(PYTHON) -m src.pipeline.build_crosswalk

# Step 3: Add Entrez IDs
$(PROCESSED_DIR)/cancer_gene_mesh_site_only_with_entrez.parquet: $(PROCESSED_DIR)/cancer_gene_disease_mesh_site_only.parquet $(NCBI_DIR)/gene2ensembl.gz
	@echo "Step 3: Adding Entrez Gene IDs..."
	$(PYTHON) -m src.pipeline.add_entrez

# Run all steps
run-pipeline:
	$(PYTHON) -m src.pipeline.run_all

# =============================================================================
# ANALYSIS
# =============================================================================

audit: $(PROCESSED_DIR)/audit_missing_mesh_report.txt

$(PROCESSED_DIR)/audit_missing_mesh_report.txt: $(PROCESSED_DIR)/cancer_diseases_mesh_crosswalk.parquet $(OT_DIR)/association_overall_direct
	@echo "Running MeSH coverage audit..."
	$(PYTHON) -m src.analysis.audit_missing_mesh

# =============================================================================
# CLEANUP
# =============================================================================

clean:
	@echo "Removing processed outputs..."
	rm -f $(PROCESSED_DIR)/*.parquet
	rm -f $(PROCESSED_DIR)/*.csv
	rm -f $(PROCESSED_DIR)/*.txt

clean-downloads:
	@echo "Removing downloaded data..."
	rm -rf $(OT_DIR)
	rm -rf $(NCBI_DIR)

clean-all: clean clean-downloads

# =============================================================================
# DEVELOPMENT
# =============================================================================

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests (if any)
test:
	$(PYTHON) -m pytest tests/ -v

# Format code
format:
	black src/
	isort src/

# Lint
lint:
	flake8 src/
	mypy src/
