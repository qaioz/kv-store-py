.PHONY: install test lint format check clean

install:
	uv sync --group dev

test:
	uv run pytest

lint:
	uv run flake8 .

format:
	uv run black .
	uv run isort .

check: format lint test

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage