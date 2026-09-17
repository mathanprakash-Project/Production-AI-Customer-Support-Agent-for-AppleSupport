.PHONY: up down build test eval smoke ingest dev-backend dev-frontend

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	pytest backend/tests -v

eval:
	python -m backend.app.eval.run

smoke:
	python -m backend.app.eval.run --smoke

ingest:
	python -m backend.app.jobs.ingest

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

