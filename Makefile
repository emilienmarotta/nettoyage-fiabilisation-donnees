.PHONY: up down generate ingest clean test

up:
	docker compose up -d

down:
	docker compose down

generate:
	python -m generator.main

ingest:
	python -m pipeline.ingest

clean:
	python -m pipeline.clean.run

test:
	pytest
