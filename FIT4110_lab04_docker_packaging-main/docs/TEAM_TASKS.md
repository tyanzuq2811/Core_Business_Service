# TEAM_TASKS.md — Nhiệm Vụ Hoàn Thành (Core Business Team)

Bảng tổng hợp các đầu việc đã hoàn thành cho **Core Business Service** (`team-core`) trong **FIT4110 Lab 04**:

---

## Danh mục công việc đã thực hiện

- [x] **Hợp đồng OpenAPI 3.1**: Chuẩn hóa `contracts/core-business.openapi.yaml` định nghĩa đầy đủ các endpoint nghiệp vụ, schema `Alert`, `AccessPolicy`, `DecisionAudit`, mã lỗi RFC 9457 `ProblemDetails`.
- [x] **Mã nguồn Backend**: Xây dựng backend FastAPI tại `src/core_app/main.py` đáp ứng 100% các endpoint trong hợp đồng.
- [x] **Endpoint Healthcheck**: Đảm bảo `GET /health` phản hồi `status: ok` phục vụ giám sát container.
- [x] **Dockerfile chuẩn công nghiệp**:
  - [x] Multi-stage build (Builder & Runtime).
  - [x] Chạy ứng dụng bằng non-root user `appuser`.
  - [x] Tích hợp Docker native `HEALTHCHECK`.
  - [x] Cấu hình động qua biến môi trường `${APP_HOST}`, `${APP_PORT}`.
- [x] **Tối ưu Build Context**: Thiết lập `.dockerignore` loại bỏ `node_modules`, `.venv`, cache, logs và reports.
- [x] **Chống Hardcode**: Cung cấp `.env.example` chuẩn, sẵn sàng chạy ngay khi clone.
- [x] **Tài liệu Hướng dẫn**: Viết chi tiết `RUN_LOCAL.md` và `README.md`.
- [x] **Kiểm thử Tự động**:
  - [x] Kiểm tra linter contract với Spectral (`npm run lint:openapi` pass 0 lỗi).
  - [x] Build Docker image `fit4110/core-business:lab04`.
  - [x] Khởi chạy container `fit4110-core-lab04`.
  - [x] Chạy toàn bộ Postman test suite (24 requests, 38 assertions pass 100%).
  - [x] Xuất báo cáo Newman XML và HTML trong thư mục `reports/`.
- [x] **CI/CD Workflow**: Thiết lập GitHub Actions workflow `.github/workflows/docker-newman.yml` cho Core Business Service.
- [x] **Gán nhãn Image**: Tag quy ước `v0.1.0-core-business`.
