.PHONY: check test fmt run-docker-test stop-docker-test

check:
	uv run ruff check .
	uv run mypy .

test:
	uv run pytest

format:
	uv run ruff format .

start-docker-test-manual:
	docker-compose -f docker-compose.test.yml up --build

start-docker-test:
	docker-compose -f docker-compose.test.yml up --build -d

stop-docker-test:
	docker-compose -f docker-compose.test.yml down -v
