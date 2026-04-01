.PHONY: lint test typecheck install

VENV := venv/bin

lint:
	$(VENV)/ruff check apps/ shared/ trainer/ tests/
	$(VENV)/ruff format --check apps/ shared/ trainer/ tests/

test:
	$(VENV)/pytest tests/ -v --tb=short

test-phase3:
	$(VENV)/pytest tests/apps/api/routers/test_phase3_integration.py -v --tb=short

typecheck:
	$(VENV)/pyright apps/ shared/

install:
	$(VENV)/pip install -e ".[dev,web,trainer,edge]"
