.PHONY: install lint build run compose-up compose-down compose-down-clean logs test-compose health

install:
	npm install

lint:
	npx spectral lint contracts/*.yaml

build:
	docker build -t smartcampus/core-business:latest .

run:
	docker run --rm --name smartcampus-core-service -p 8001:8000 --env-file .env smartcampus/core-business:latest

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-down-clean:
	docker compose down -v

logs:
	docker compose logs -f

health:
	@echo "=== 1. API Core Business (host 8001) ==="
	curl -s http://localhost:8001/health | python -m json.tool

status:
	@echo "=== LAN Network Integration Status (All Partners) ==="
	curl -s http://localhost:8001/integrations/status | python -m json.tool

test-compose:
	npm run test:compose