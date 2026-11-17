# Changelog — Core Business Service (`team-core`)

Tất cả các thay đổi đáng chú ý qua từng giai đoạn phát triển từ Lab 01 đến Lab 05 (Ready for Plug-a-thon & Demo).

## [0.5.0] - 2026-11 (Lab 05 Release — Plug-a-thon & Production Readiness)

### Added
- **Dual Storage Layer (`src/core_app/storage.py`)**: Hỗ trợ chuyển đổi linh hoạt giữa **PostgreSQL 15** (`PostgresStore`) khi chạy Docker Compose và **In-Memory** (`InMemoryStore`) khi chạy cục bộ thông qua biến môi trường `STORAGE_BACKEND=postgres|memory` (có tùy chọn comment/bỏ comment nhanh trong code và `.env`).
- **Docker Compose Mock Integration (`docker-compose.mock.yml`)**: File override để khi chạy `docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock up -d --build`, container `api` kết nối trực tiếp tới toàn bộ 5 mock service (`ai-vision-mock`, `iot-mock`, `gate-mock`, `analytics-mock`, `notify-mock`).
- **Real Notification & Integration Config Endpoints**:
  - `GET /integrations/config`: Cung cấp cấu hình đối tác, MQTT broker và `storageBackend` động cho Live Operations Dashboard.
  - `POST /integrations/notification/send`: Chủ động chuyển tiếp cảnh báo qua Notification Service (`POST /notifications/send`), kết hợp tự động bắn thông báo khi phát sinh alert mức `HIGH` / `CRITICAL`.
- **Complete Mock Service Parity**: Mở rộng `gate_mock` (`/cards/{card_id}`, `/access/logs/recent`, `/gates/{gate_id}/status`), `ai_service` (`/vision/detect`, `/vision/models/info`, `/vision/detections/{detection_id}`, `/vision/results/recent`) và `notify_mock` (`GET /notifications`).
- **Demo Pack Documentation**: `changelog.md`, `endpoint_catalog.md`, `docs/architecture_one_pager.md`, `evidence/`, `reflection/`.

### Changed
- **Non-blocking Async Performance**: Đưa toàn bộ tác vụ `publish_mqtt_event` và `dispatch_notification` vào `FastAPI BackgroundTasks`, đồng thời song song hóa `GET /integrations/status` qua `asyncio.gather` + `anyio.to_thread.run_sync`, đảm bảo SLA `< 200ms` cho `POST /access/check` ngay cả khi MQTT/Notification ở trạng thái offline.
- **Business Rule & Idempotency Enforcement**:
  - `POST /access/check` thực thi chính sách `POL-001`: kiểm tra cổng hợp lệ (`GATE-01`, `GATE-02`), danh sách thẻ đen, khung giờ (`06:00-22:00`), giới hạn tần suất quẹt thẻ trong 60 giây và kiểm tra trùng `idempotencyKey` trả về chuẩn `409 Conflict`. Khi `DENY`, tự động tạo `Alert` và phát MQTT `business.policy.decision.created` đúng schema `decision_id, policy_type, decision, location, subject_type, decided_at`.
  - `POST /alerts/{alert_id}/resolve` chuyển trạng thái `RESOLVED`, ghi nhận `resolvedAt` và phát MQTT `business.alert.resolved`.
  - `POST /alerts` xác thực `Bearer` token đối chiếu trực tiếp `AUTH_TOKEN` trong biến môi trường và trả kèm `relatedEventId`.
  - `POST /events` hỗ trợ cả payload lồng OpenAPI (`metric`/`value`) lẫn payload phẳng (`temperature`/`humidity`/`motion`) và tự tạo Alert khi vượt ngưỡng nhiệt độ.
- **Dynamic Operations Dashboard (`dashboard.html`)**: Loại bỏ toàn bộ IP tĩnh `192.168.1.x` và token hardcode; tải cấu hình động từ `/integrations/config`, bổ sung badge hiển thị Storage backend (`POSTGRES` / `MEMORY`), nút kiểm thử Notification Send và cơ chế chống chồng lặp `fetchAllData()`.
- **OpenAPI 3.1.0 & Newman Test Suite**: Đồng bộ `contracts/core-business.openapi.yaml` (Lab 05) và `FIT4110_lab02_openapi-main/openapi.yaml`, bổ sung Spectral `.spectral.yaml` pass 0 errors; nâng cấp Postman collection sử dụng `{{$guid}}`, kiểm thử `409 Conflict`, `DENY` rule, `/resolve`, `/vision/detection-result`, `< 200ms` SLA và tích hợp 5 mock services.

---

## [0.4.0] - Lab 04 (Container Packaging)
- Đóng gói FastAPI service bằng Multi-stage `Dockerfile`, chạy dưới tài khoản non-root `appuser`, native `HEALTHCHECK` và chạy Newman kiểm thử tự động trong container.

## [0.3.0] - Lab 03 (Postman, Prism Mock & CI)
- Xây dựng kịch bản kiểm thử 6 nhóm (Health, Happy Path, Auth, Negative RFC 9457 ProblemDetails, Boundary, Non-functional SLA) chạy trên Prism Mock & Newman.

## [0.2.0] - Lab 02 (Contract-First OpenAPI 3.1.0)
- Thiết kế `openapi.yaml` chuẩn OAS 3.1.0, bổ sung `POST /vision/detection-result` (AI Vision webhook) và chuẩn hóa Async MQTT Contracts (`event-contract-04`, `event-contract-05`, `event-contract-08`).

## [0.1.0] - Lab 01 (Service Boundary)
- Xác định phạm vi trách nhiệm (In-scope / Out-of-scope), kiến trúc luồng dữ liệu Upstream/Downstream của `Core Business Service`.
