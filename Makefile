ENV ?= dev
ENV_FILE = .env.$(ENV)

# --- BIẾN MÔI TRƯỜNG ---
COMPOSE_FILE = infras/compose/docker-compose.$(ENV).yml

# Báo cho Make biết đây là các lệnh, không phải là tên file
.PHONY: up down build logs shell sync ingest

# --- CÁC LỆNH DOCKER ---
up:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d

down:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) down

build:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) build

build-nocache:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) build --no-cache

logs-dev:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) logs -f

# Vào thẳng terminal của container postgres để test DB
db-shell:
	docker exec -it mads-postgres psql -U admin -d ecommerce

# --- CÁC LỆNH BACKEND (Chạy ở máy Local) ---
# Vì thư mục gốc không có uv.lock, phải cd vào backend rồi mới chạy lệnh
sync:
	cd backend && uv sync

# --- CÁC LỆNH CHẠY TASK ---
# Chạy thủ công container ingestion rồi tự xóa container sau khi chạy xong
ingest:
	docker compose -f $(COMPOSE_FILE) run --rm ingestion