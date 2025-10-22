.PHONY: check test fmt start-docker-test start-docker-test-manual stop-docker-test

check:
	uv run ruff check .
	uv run mypy .

test:
	uv run pytest

format:
	uv run ruff format .

build-toc:
	# https://github.com/jonschlinkert/markdown-toc
	markdown-toc -i README.md

start-docker-test-manual:
	docker compose -f docker-compose.test.yml up --build

start-docker-test:
	docker compose -f docker-compose.test.yml up --build -d

stop-docker-test:
	docker compose -f docker-compose.test.yml down -v
