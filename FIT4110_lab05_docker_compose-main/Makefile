.PHONY: install lint lint-compose build run compose-up compose-mock-up compose-down compose-mock-down compose-down-clean logs test-compose health status

install:
	npm install

lint:
	npx spectral lint contracts/*.yaml

lint-compose:
	docker compose config --quiet
	docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock config --quiet

build:
	docker build -t fit4110/core-business:lab05 .

run:
	docker run --rm --name fit4110-core-lab05 -p 8001:8000 --env-file .env.example fit4110/core-business:lab05

compose-up:
	docker compose up -d --build --wait

compose-mock-up:
	docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock up -d --build --wait

compose-down:
	docker compose down

compose-mock-down:
	docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock down

compose-down-clean:
	docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock down -v

logs:
	docker compose logs -f

health:
	@echo "=== 1. API Core Business (host 8001) ==="
	curl -s http://localhost:8001/health | python -m json.tool

status:
	@echo "=== Integration Status (All 5 Partners) ==="
	curl -s http://localhost:8001/integrations/status | python -m json.tool

test-compose:
	npm run test:compose
