# Makefile for NetBox Component Synchronization Development

.PHONY: help install test test-all format lint clean check pre-commit

help:
	@echo "Available commands:"
	@echo "  install     - Install development dependencies"
	@echo "  test        - Run validation tests (works everywhere)"
	@echo "  test-all    - Run all available tests"
	@echo "  format      - Format code with black and isort"
	@echo "  lint        - Run linting with flake8"
	@echo "  check       - Run format and lint checks"
	@echo "  pre-commit  - Install pre-commit hooks"
	@echo "  clean       - Clean build artifacts and cache"

install:
	pip install -e .
	pip install -r .github/test-requirements.txt

test:
	python run_tests.py --test-type validation --verbose

test-all:
	python run_tests.py --verbose

format:
	black .
	isort .

lint:
	flake8 .

check: format lint test

pre-commit:
	pip install pre-commit
	pre-commit install

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.coverage" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# CI-specific targets
ci-test:
	python run_tests.py --pytest --verbose

ci-format-check:
	black --check --diff .
	isort --check-only --diff .
	flake8 .