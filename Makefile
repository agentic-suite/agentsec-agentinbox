# agentinbox — developer entry points.
#
# The standalone rule: the runtime has no third-party dependencies, and every target below
# uses only the project's own virtualenv. `make setup` is idempotent.

VIRTUAL_ENV ?= .venv
PYTHON ?= python3
PY := $(VIRTUAL_ENV)/bin/python
PIP := $(VIRTUAL_ENV)/bin/pip

.PHONY: setup lint typecheck test cov gate clean packs scan claims evidence compat sbom posture

setup: $(VIRTUAL_ENV)/bin/python
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -e ".[dev]"
	@$(PY) -c "import agentinbox; print('agentinbox', agentinbox.__version__)"

$(VIRTUAL_ENV)/bin/python:
	$(PYTHON) -m venv $(VIRTUAL_ENV)

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy

test:
	$(PY) -m pytest

cov:
	$(PY) -m pytest --cov=agentinbox --cov-report=term-missing --cov-fail-under=95

# Single milestone gate: the WBS runs these once at milestone end, never per ticket.
gate: lint typecheck test cov claims evidence compat

# Release-blocking security checks (M22).
packs:
	$(PY) -m agentinbox.packs

scan:
	$(PY) -m agentinbox.scanner --self-test

claims:
	$(PY) -m agentinbox.claimslint

evidence:
	$(PY) -m agentinbox.scanner --self-test
	$(PY) -m agentinbox.scanner --path docs/release/v0.1.0
	$(PY) -m agentinbox.scanner --path docs/field-test/v0.1.0
	$(PY) -m agentinbox.scanner --path field-test/v0.1.0/results

compat:
	$(PY) -m agentinbox.compatmatrix --check

sbom:
	$(PY) -m agentinbox.posture sbom

posture:
	$(PY) -m agentinbox.posture manifest
	$(PY) -m agentinbox.posture security-txt

clean:
	rm -rf $(VIRTUAL_ENV) .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -name '*.egg-info' -type d -prune -exec rm -rf {} +
