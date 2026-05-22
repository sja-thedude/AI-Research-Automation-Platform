.PHONY: help build up down logs migrate makemigrations superuser seed shell test lint fmt worker beat

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

build:  ## Build docker images
	docker compose build

up:  ## Start the full stack
	docker compose up -d

down:  ## Stop the stack
	docker compose down

logs:  ## Tail logs
	docker compose logs -f web worker

migrate:  ## Apply migrations
	docker compose run --rm web python manage.py migrate

makemigrations:  ## Generate migrations
	docker compose run --rm web python manage.py makemigrations

superuser:  ## Create a Django superuser
	docker compose run --rm web python manage.py createsuperuser

seed:  ## Seed a demo user + team
	docker compose run --rm web python manage.py seed_demo

shell:  ## Django shell_plus
	docker compose run --rm web python manage.py shell

test:  ## Run the test suite
	docker compose run --rm web pytest

lint:  ## Lint with ruff
	ruff check apps config

fmt:  ## Format with black + ruff --fix
	black apps config && ruff check --fix apps config
