.PHONY: dev gateway agent eval test lint fmt clean

# START FULL LOCAL STACK
dev:
	docker compose up -d postgres redis prometheus grafana
	@echo "Stack ready. Postgres:5432 Redis:6379 Grafana:3000"

# STOP STACK
down:
	docker compose down

# RUN GATEWAY
gateway:
	uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000

# RUN BENCHMARKS
eval:
	python -m evaluation.runners.benchmark --suite general

eval-safety:
	python -m evaluation.runners.benchmark --suite safety

eval-scientific:
	python -m evaluation.runners.benchmark --suite scientific

eval-ci:
	python -m evaluation.runners.ci --baseline benchmarks/results/baseline.json

# SERVING BENCHMARKS
bench-serving:
	python -m serving.benchmarks.harness --concurrency 1 2 4 8 16 32

# TESTS
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-chaos:
	pytest tests/chaos/ -v

# CODE QUALITY
lint:
	ruff check .
	mypy gateway/ agent/ evaluation/

fmt:
	ruff format .
	ruff check --fix .

# INSTALL
install:
	pip install -e ".[dev]"

# CLEAN
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build
