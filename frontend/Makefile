.PHONY: help install dev build test lint format check clean

help:
	@echo "Frontend Development Commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Start development server"
	@echo "  make build      - Build for production"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Format code"
	@echo "  make check      - Type check with svelte-check"
	@echo "  make clean      - Remove build artifacts"

install:
	npm install

dev:
	npm run dev

build:
	npm run build

test:
	npm test

lint:
	npm run lint

format:
	npm run format

check:
	npm run check

clean:
	rm -rf node_modules dist .svelte-kit
