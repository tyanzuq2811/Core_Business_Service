# RUN_COMPOSE.md — Vận Hành Core Business Service (Smart Campus Operations Platform)

Hướng dẫn triển khai **Core Business Service** trên 2 chế độ:
1. **Local Mock Integration (`--profile mock`)**: Chạy trọn bộ Core + PostgreSQL + 5 Mock Services trên 1 máy để kiểm thử khép kín.
2. **Plug-a-thon LAN Mode**: Kết nối trực tiếp tới máy của các nhóm đối tác thật trong cùng mạng Wi-Fi/LAN.

---

## 1. Danh Sách Dịch Vụ & Port Chuẩn

| Service | Tên Container | Host Port | Container Port | Vai Trò |
|---|---|---:|---:|---|
| **Core Business API** | `smartcampus-core-service` | `8001` | `8000` | API trung tâm, Rule Engine, Live Dashboard (`http://localhost:8001/dashboard`) |
| **PostgreSQL 15 DB** | `smartcampus-core-db` | `5433` | `5432` | Lưu trữ bền vững alerts, policies, decisions, events, idempotency keys |
| **AI Vision Mock** *(profile `mock`)* | `smartcampus-ai-mock` | `9001` | `9000` | Giả lập `/vision/face-match`, `/vision/detect`, `/vision/models/info` |
| **IoT Mock** *(profile `mock`)* | `smartcampus-iot-mock` | `9002` | `9000` | Giả lập `/health`, `/telemetry` |
| **Access Gate Mock** *(profile `mock`)* | `smartcampus-gate-mock` | `9003` | `9000` | Giả lập `/cards/{cardId}`, `/gates/{gateId}/status`, `/access/logs/recent` |
| **Analytics Mock** *(profile `mock`)* | `smartcampus-analytics-mock` | `9004` | `9000` | Giả lập `/health`, `/metrics/summary` |
| **Notification Mock** *(profile `mock`)* | `smartcampus-notify-mock` | `9005` | `9000` | Giả lập `/notifications/send` và `GET /notifications` |

---

## 2. Chuyển Đổi Kiểu Lưu Trữ (Dual Storage: PostgreSQL & In-Memory)

Core Business hỗ trợ cả **2 kiểu lưu trữ** trong `src/core_app/storage.py`:

- **Chế độ `postgres` (mặc định Docker Compose)**: Dữ liệu lưu vào PostgreSQL (`smartcampus-core-db`).
- **Chế độ `memory` (In-Memory RAM)**: Tiện chạy cục bộ bằng Uvicorn không cần Postgres.

Mở file `.env` (copy từ `.env.example`) và mở/comment 1 trong 2 dòng:
```env
STORAGE_BACKEND=postgres
# STORAGE_BACKEND=memory
```
Hoặc có thể comment/bỏ comment trực tiếp biến `backend = "postgres"` / `backend = "memory"` trong hàm `create_store()` tại `src/core_app/storage.py`.

---

## 3. Chạy Kịch Bản 1: Full Local Mock Stack (`--profile mock`)

Dùng file override `docker-compose.mock.yml` để container `api` gọi trực tiếp tới `http://*-mock:9000` trong mạng nội bộ `smartcampus-network`:

```powershell
# 1. Tạo .env (nếu chưa có)
Copy-Item .env.example .env

# 2. Cài đặt gói Node cho Spectral & Newman (lần đầu)
npm install

# 3. Kiểm tra OpenAPI & cú pháp Docker Compose
npm run lint:openapi
npm run lint:compose

# 4. Khởi chạy Core Business + PostgreSQL + 5 Mock Services
docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock up -d --build --wait

# 5. Mở Live Web Dashboard
Start-Process http://localhost:8001/dashboard

# 6. Chạy bộ kiểm thử tự động Newman (sinh reports/newman-lab05-compose.html & .xml)
npm run test:compose

# 7. Dừng hệ thống
docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock down
```

---

## 4. Chạy Kịch Bản 2: Plug-a-thon LAN Mode

Khi kết nối với máy thật của các nhóm khác trong cùng mạng LAN:
1. Mở `.env` cập nhật IP thật (`IOT_SERVICE_URL`, `GATE_SERVICE_URL`, `AI_VISION_URL`, `ANALYTICS_SERVICE_URL`, `MQTT_BROKER_HOST`, `NOTIFICATION_SERVICE_URL`).
2. Khởi chạy chỉ Core API + PostgreSQL:
   ```powershell
   docker compose up -d --build --wait
   ```
3. Kiểm tra trạng thái đồng thời 5 nhóm:
   ```powershell
   curl http://localhost:8001/integrations/status
   ```
   Hoặc mở tab **🌐 6. Radar Toàn Mạng & Hợp Đồng** trên `http://localhost:8001/dashboard`.

---

## 5. Trung Tâm Điều Khiển Live Operations Dashboard (`http://localhost:8001/dashboard`)

Dashboard tải toàn bộ địa chỉ đối tác, cấu hình MQTT và chế độ Storage động từ `GET /integrations/config`:
- **Tab 1 — Access Gate**: Kéo logs RFID, tra cứu thẻ `GET /cards/{cardId}`, trạng thái barrier, giả lập quẹt thẻ `POST /access/check`.
- **Tab 2 — AI Vision**: Xem danh sách cảnh báo an ninh, test `face-match` / `YOLO detect` / `models`, giả lập webhook/alert.
- **Tab 3 — IoT Ingestion**: Theo dõi luồng sự kiện `POST /events`, giả lập nhiệt độ quá ngưỡng `42.5°C` tự sinh Alert.
- **Tab 4 — Analytics**: Bắn sự kiện kiểm thử MQTT (`business.alert.created`, `business.policy.decision.created`, `business.alert.resolved`) lên `business.events`.
- **Tab 5 — Notification**: Kiểm tra `/health` và gửi thử thông báo `POST /notifications/send` qua Notification Service.
- **Tab 6 — Radar Toàn Mạng & Hợp Đồng**: Giám sát ONLINE/OFFLINE thời gian thực và độ trễ ping 5 dịch vụ đối tác.
