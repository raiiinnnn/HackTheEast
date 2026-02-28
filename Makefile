.PHONY: up down backend-dev backend-migrate frontend-dev logs

up:
	docker-compose up -d

down:
	docker-compose down

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-migrate:
	cd backend && alembic upgrade head

backend-migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

frontend-dev:
	cd frontend && npx expo start

logs:
	docker-compose logs -f

db-shell:
	docker-compose exec db psql -U postgres -d focusfeed
