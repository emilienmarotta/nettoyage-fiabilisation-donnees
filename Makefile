.PHONY: up down generate ingest run test

up:
	docker compose up -d

down:
	docker compose down

generate:
	python -m generator.main

ingest:
	python -m pipeline.ingest

run:
	python -m pipeline.run

test:
	pytest
