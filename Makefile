.PHONY: install test lint format clean run dev help

help:
	@echo "RivaAI Development Commands"
	@echo "============================"
	@echo "install    - Install dependencies"
	@echo "test       - Run all tests"
	@echo "test-unit  - Run unit tests only"
	@echo "test-prop  - Run property-based tests only"
	@echo "lint       - Run linters"
	@echo "format     - Format code"
	@echo "clean      - Clean build artifacts"
	@echo "run        - Run the application"
	@echo "dev        - Run in development mode with auto-reload"

install:
	poetry install

test:
	poetry run pytest -v

test-unit:
	poetry run pytest -v -m "not property"

test-prop:
	poetry run pytest -v -m property

lint:
	poetry run ruff check rivaai tests
	poetry run mypy rivaai

format:
	poetry run black rivaai tests
	poetry run ruff check --fix rivaai tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build dist .pytest_cache .coverage htmlcov

run:
	poetry run python -m rivaai.main

dev:
	poetry run uvicorn rivaai.main:app --reload --host 0.0.0.0 --port 8000
