.PHONY: install test lint format check clean

install:
	pip install -e .[dev]

test:
	pytest

lint:
	flake8 .

format:
	black .
	isort .

check: format lint test

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage