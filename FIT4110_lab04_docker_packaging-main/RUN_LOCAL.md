# RUN_LOCAL.md — Hướng Dẫn Chạy & Kiểm Thử Container (Core Business Service)

Tài liệu này hướng dẫn các bước chi tiết để đóng gói, khởi chạy container và kiểm thử tự động cho **Core Business Service** trong **FIT4110 Lab 04**.

> **Yêu cầu môi trường**:
> - Docker Desktop hoặc Docker Engine đã được cài đặt và đang chạy.
> - Node.js >= 18 và npm để chạy Newman test suite.

---

## 1. Clone repo & Cài đặt phụ thuộc

```bash
git clone <repo-url>
cd FIT4110_lab04_docker_packaging-main

# Cài đặt phụ thuộc Newman, Spectral, Prism
npm install
```

---

## 2. Cấu hình Biến Môi Trường

File `.env.example` đã chứa sẵn cấu hình mặc định an toàn để chạy ngay mà không cần chỉnh sửa:

```env
APP_HOST=0.0.0.0
APP_PORT=8000
AUTH_TOKEN=mock-core-token-2026
SERVICE_NAME=core-business
SERVICE_VERSION=0.4.0
ENV=local
```

Nếu muốn tùy chỉnh cấu hình riêng:
```bash
cp .env.example .env
# Chỉnh sửa file .env theo nhu cầu (PORT, TOKEN, v.v.)
```

---

## 3. Kiểm tra OpenAPI Contract

Trước khi build image, kiểm tra tính hợp lệ của hợp đồng OpenAPI 3.1.0:

```bash
npm run lint:openapi
```
*(Kết quả mong đợi: `No results with a severity of 'error' found!`)*

---

## 4. Build Docker Image

Build image cho Core Business Service với multi-stage build:

```bash
docker build -t fit4110/core-business:lab04 .
```

Hoặc sử dụng Makefile:
```bash
make build
```

---

## 5. Khởi chạy Docker Container

Khởi chạy container ở chế độ nền (detached):

```bash
docker run -d   --name fit4110-core-lab04   -p 8000:8000   --env-file .env.example   fit4110/core-business:lab04
```

Hoặc sử dụng Makefile:
```bash
make run-detached
```

### Kiểm tra Healthcheck:
```bash
curl http://localhost:8000/health
```

Kết quả phản hồi mong đợi:
```json
{
  "status": "ok",
  "service": "core-business",
  "version": "0.4.0",
  "time": "2026-08-22T08:00:00Z"
}
```

Kiểm tra trạng thái Healthcheck của Docker daemon:
```bash
docker ps
```
*(Cột STATUS sẽ hiển thị `Up ... (healthy)`)*

---

## 6. Chạy Newman Test Suite trên Container

Chạy toàn bộ 24 test cases kiểm thử hợp đồng tự động:

```bash
npm run test:local
```

Hoặc sử dụng Makefile:
```bash
make test-docker
```

Báo cáo kiểm thử tự động được ghi nhận tại:
- `reports/newman-lab04-local.xml` (Báo cáo JUnit XML)
- `reports/newman-lab04-local.html` (Báo cáo HTML Extra trực quan)

---

## 7. Dừng Container & Dọn dẹp

```bash
docker stop fit4110-core-lab04
docker rm fit4110-core-lab04
```

Hoặc sử dụng Makefile:
```bash
make stop
```

---

## 8. Xử lý Sự cố Nhanh

| Hiện tượng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| Lỗi xung đột port `8000` | Port 8000 đang được tiến trình khác sử dụng | Đổi port map: `-p 8001:8000` và cập nhật `baseUrl` trong postman environment |
| Docker daemon chưa chạy | Docker Desktop đang tắt | Khởi động Docker Desktop và đợi trạng thái Engine sẵn sàng |
| Auth test bị từ chối 401 | Sai `AUTH_TOKEN` | Đảm bảo biến môi trường và Postman environment đồng bộ token |
