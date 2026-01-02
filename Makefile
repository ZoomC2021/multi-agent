# Makefile for multi-agent-consensus

# Variables
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: all
all: venv

$(VENV)/bin/activate: requirements.txt pyproject.toml
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	touch $(VENV)/bin/activate

.PHONY: venv
venv: $(VENV)/bin/activate

.PHONY: install
install: venv

.PHONY: run
run: venv
	$(PYTHON) -m consensus_system.cli $(ARGS)

.PHONY: test
test: venv
	$(PYTHON) -m pytest

.PHONY: lint
lint: venv
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .

.PHONY: format
format: venv
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/black .

.PHONY: find-bugs
find-bugs: venv
	@$(PYTHON) -m bug_finder.cli $(if $(DIFF),--diff,) $(ARGS) $(or $(TARGET),.)

.PHONY: bug-viewer
bug-viewer: venv
	@$(VENV)/bin/pip install streamlit
	@$(PYTHON) -m bug_finder.viewer

.PHONY: review-pr
review-pr: venv
	@if [ -z "$(PR)" ]; then \
		echo "Usage: make review-pr PR=<number> [REPO=owner/repo] [ARGS=...]"; \
		echo "Example: make review-pr PR=123"; \
		echo "Example: make review-pr PR=456 REPO=facebook/react"; \
		exit 1; \
	fi
	@$(PYTHON) -m bug_finder.cli --pr $(PR) $(if $(REPO),--repo $(REPO),) $(ARGS)

.PHONY: clean
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache

.PHONY: help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  venv        Create virtual environment and install dependencies"
	@echo "  install     Alias for venv"
	@echo "  run         Run the consensus-cli (use ARGS=\"...\" for options)"
	@echo "  test        Run tests using pytest"
	@echo "  lint        Check code style with ruff and black"
	@echo "  format      Format code with ruff and black"
	@echo "  find-bugs   Run the bug finder (use TARGET=\"path\" or DIFF=1)"
	@echo "  review-pr   Review a GitHub PR (use PR=<number> REPO=owner/repo)"
	@echo "  bug-viewer  Run the streamlit bug report viewer"
	@echo "  clean       Remove virtual environment and cache files"
	@echo "  help        Show this help message"
