.PHONY: install \
        build install-local \
        data data-rules data-cards data-prints \
        install-db install-db-cards install-db-rules check-db \
        server mcp \
        lint test \
        clean

PYTHON := python
PIP    := pip
MCP    := $(shell $(PYTHON) -c "import shutil; print(shutil.which('mcp') or 'mcp')")

# ── Setup ─────────────────────────────────────────────────────────────────────

# Full local setup: install deps + build all data + build binary + copy to ~/karnData/arsenal/
local: install data install-local

install:
	$(PIP) install -e ".[dev]"

# ── Build data locally (generates DB artifacts in db/) ────────────────────────

data-rules:
	$(PYTHON) scripts/build_rules.py --force-download

data-cards:
	$(PYTHON) scripts/build_db.py

data-prints:
	$(PYTHON) scripts/build_prints.py --force

# data-cards already builds prints.db internally (step 8/9 of build_db.py)
data: data-rules data-cards

# ── Install DBs from GitHub Releases (downloads pre-built artifacts) ──────────

install-db-cards:
	$(PYTHON) scripts/install_data.py --component cards

install-db-rules:
	$(PYTHON) scripts/install_data.py --component rules

install-db:
	$(PYTHON) scripts/install_data.py

check-db:
	$(PYTHON) -c "from scripts.install_data import check_db_versions; import json; print(json.dumps(check_db_versions(), indent=2))"

# ── Executable ────────────────────────────────────────────────────────────────

# Build binary via PyInstaller (output: dist/karn or dist/karn.exe)
build:
	$(PYTHON) scripts/build_executables.py

# Build + copy to ~/karnData/arsenal/ so karnforge picks it up locally
install-local: build
	$(PYTHON) scripts/install_local.py

# ── Run ───────────────────────────────────────────────────────────────────────

# Run server directly (no binary needed — good for fast iteration)
server:
	$(PYTHON) -m arsenal.server

# MCP dev inspector — opens browser UI to call tools interactively
mcp:
	$(MCP) dev arsenal/server.py

# ── Quality ───────────────────────────────────────────────────────────────────

# Mirror exactly what ci.yml runs
lint:
	ruff check .

test:
	$(PYTHON) -m pytest

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	rm -rf dist/ build/

# ── Releasing (reference) ─────────────────────────────────────────────────────
# Releases are triggered by git tags — CI handles the rest:
#
#   Server:   git tag server-v1.2.0 && git push --tags
#             → CI builds win/mac/linux binaries → uploads to GitHub Release
#
#   Cards DB: git tag cards-db-v1.1.0 && git push --tags
#             → CI runs build_db.py (~60 min) → uploads karn-cards-db-v1.1.0.tar.gz
#
#   Rules DB: auto-tagged monthly by update-rules.yml
#             → manual: git tag rules-db-v1.0.1 && git push --tags
#
# To manually upload a local artifact to an existing release:
#   python scripts/upload_data.py --component cards --release cards-db-v1.1.0
#   python scripts/upload_data.py --component rules --release rules-db-v1.0.1
