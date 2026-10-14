.PHONY: up down generate ingest clean dbt test

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

dbt:
	cd dbt_project && dbt build

test:
	pytest
