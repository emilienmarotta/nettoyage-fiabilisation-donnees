.PHONY: up down generate run test

up:
	docker compose up -d

down:
	docker compose down

generate:
	python -m generator.main

run:
	python -m pipeline.run

test:
	pytest
