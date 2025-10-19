.PHONY: check test fmt

check:
	uv run ruff check .
	uv run mypy .

test:
	uv run pytest

format:
	uv run ruff format .
