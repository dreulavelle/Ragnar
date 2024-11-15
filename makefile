.PHONY: help install run clean test push format sort ready

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  install   Install dependencies using poetry"
	@echo "  run       Run the application"
	@echo "  test      Run the tests"
	@echo "  format    Format the code"
	@echo "  sort      Sort the imports"
	@echo "  clean     Clean up build artifacts"
	@echo "  ready     Format, sort, and clean up the code"
	@echo "  push      Push the code to the remote repository"

install:
	@poetry install --without dev

run:
	@poetry run python src/main.py

du:
	@docker compose up --build -d
	@docker compose logs -f

dd:
	@docker compose down

dr:
	@docker compose down --rmi all
	@docker image prune -f

clean:
	@find . -type f -name "*.log" -delete
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".ruff_cache" -exec rm -rf {} +

format:
	@poetry run ruff check --fix src/

sort:
	@poetry run isort src/

ready: format sort clean