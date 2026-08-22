# Docker Readiness Checklist — Core Business Service

Checklist sẵn sàng đóng gói và triển khai container cho **Core Business Service**:

## 1. Dockerfile
- [x] Base image hợp lý (`python:3.11-slim`).
- [x] Áp dụng Multi-stage build (Builder stage & Runtime stage).
- [x] Có `WORKDIR /app`.
- [x] Copy dependency (`requirements.txt`) trước source code để tối ưu Docker layer cache.
- [x] Có khai báo `EXPOSE ${APP_PORT}`.
- [x] Có chỉ thị `CMD` khởi chạy ứng dụng FastAPI qua Uvicorn.
- [x] Có `HEALTHCHECK` tự động thăm dò `GET /health`.
- [x] Chạy bằng non-root user (`appuser` thuộc `appgroup`).
- [x] Không chứa bất kỳ hardcode secret hay IP nào trong image.

## 2. Runtime
- [x] Container khởi chạy ổn định (`docker run`).
- [x] Port mapping chính xác (`-p 8000:8000`).
- [x] Endpoint `GET /health` trả về HTTP 200 `{"status": "ok", ...}`.
- [x] Trạng thái container chuyển sang `healthy` sau thời gian thăm dò.
- [x] Toàn bộ cấu hình được nạp qua biến môi trường (`.env.example`).

## 3. Testing & Verification
- [x] Hợp đồng OpenAPI 3.1.0 pass Spectral linter (`npm run lint:openapi`).
- [x] Chạy toàn bộ Postman Test Suite trên container (`npm run test:local`).
- [x] Toàn bộ 24/24 requests và 38/38 assertions đều pass thành công (0 failed).
- [x] Báo cáo Newman XML và HTML sinh đầy đủ trong thư mục `reports/`.

## 4. Documentation & Portability
- [x] Có đầy đủ `RUN_LOCAL.md` hướng dẫn các bước chạy cho máy khác khi `git clone`.
- [x] Có `.dockerignore` và `.gitignore` loại bỏ toàn bộ rác build.
- [x] Image được gắn tag chuẩn: `fit4110/core-business:lab04` và `v0.1.0-core-business`.
