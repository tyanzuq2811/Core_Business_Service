# Readiness Checklist – Core Business Service Stack (Smart Campus)

Danh sách kiểm tra mức độ sẵn sàng của **Core Business Service (`team-core`)** cho kết nối liên dịch vụ (Docker Compose Mock & LAN Plug-a-thon) và báo cáo đồ án:

- [x] **Contract & Lint:** Hợp đồng OpenAPI 3.1.0 (`contracts/core-business.openapi.yaml`) đồng bộ với `FIT4110_lab02_openapi-main/openapi.yaml` và pass Spectral lint (`npm run lint:openapi`) không có lỗi.
- [x] **Database & Dual Storage ready:** Container `smartcampus-core-db` (PostgreSQL 15) cấu hình `pg_isready` healthcheck; `src/core_app/storage.py` hỗ trợ chuyển đổi linh hoạt `STORAGE_BACKEND=postgres` và `STORAGE_BACKEND=memory`.
- [x] **API Core Business ready:** `http://localhost:8001/health` trả `200 OK` kèm trường `storage` (`postgres`/`memory`); `POST /access/check` đạt SLA `< 200ms`.
- [x] **Real Business Rules & Idempotency:** Thực thi chính sách `POL-001` (`ALLOW`/`DENY`), `409 Conflict` khi trùng `idempotencyKey`, `POST /alerts/{id}/resolve`, tự động tạo Alert khi nhiệt độ > 40°C hoặc AI Vision risk `HIGH`/`CRITICAL`.
- [x] **Environment & Zero-Hardcode:** `.env.example` cấu hình đầy đủ cổng, token, ngưỡng rule, MQTT và URL đối tác; `dashboard.html` nạp cấu hình động từ `/integrations/config`; `docker-compose.yml` dùng `env_file` `required: false`.
- [x] **Mock Stack Integration (`docker-compose.mock.yml`):** Profile `mock` đấu nối `api` trực tiếp tới 5 mock services (`9001..9005`), hỗ trợ đẩy Notification (`POST /notifications/send`) và MQTT (`business.events`).
- [x] **Non-root Container & Healthcheck:** Container `api` chạy bằng user `appuser` (non-root) và phụ thuộc DB qua `condition: service_healthy`.
- [x] **Automated Test Suite (Newman):** Bộ test collection kiểm chứng đầy đủ Health, Functional, Auth (401), Negative ProblemDetails (404/409/422/500), Boundary, SLA `< 200ms` và tích hợp 5 dịch vụ.
