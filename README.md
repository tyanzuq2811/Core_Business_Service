# Smart Campus Operations Platform — Core Business Service

**Học phần:** FIT4110 – Dịch vụ kết nối và Công nghệ nền tảng  
**Dự án Case Study:** Smart Campus Operations Platform  
**Phân hệ đảm nhiệm:** **Core Business Service** (`team-core`)  
**Repository:** [tyanzuq2811/Core_Business_Service](https://github.com/tyanzuq2811/Core_Business_Service.git)  

---

## 👥 Bảng Phân Chia Công Việc & Tỷ Lệ Đóng Góp Nhóm (Lab 02 – Lab 05)

| STT | Mã Sinh Viên | Họ và Tên | Lớp | Tỷ Lệ Thực Hiện |
| :---: | :---: | :---| :---: | :---: |
| **1** | **1771020189** | **Lê Tuấn Dũng** *(Trưởng nhóm)* | **KHMT 17-01** | **35%** |
| **2** | 1771040024 | Nguyễn Duy Thuận | KHMT 17-01 | 25% |
| **3** | 1771040025 | Nguyễn Văn Tiến | KHMT 17-01 | 20% |
| **4** | 1771040011 | Bế Quang Hải | KHMT 17-01 | 20% |

---

## 1. Giới thiệu Tổng quan về Core Business Service

**Core Business Service** đóng vai trò là "bộ não" trung tâm điều phối nghiệp vụ và thực thi chính sách (Policy Engine) trong hệ sinh thái **Smart Campus Operations Platform**. 

Service có nhiệm vụ:
- **Tiếp nhận sự kiện** từ các phân hệ thu thập dữ liệu: Dữ liệu cảm biến môi trường (**IoT Ingestion**), sự kiện quẹt thẻ kiểm soát ra/vào cổng (**Access Gate**), và kết quả nhận diện thị giác máy tính (**AI Vision**).
- **Đánh giá và thực thi chính sách**: Kiểm tra tính hợp lệ của lượt ra/vào theo thời gian thực (định dạng thẻ `RFID-YYYY-NNN`, hướng `IN`/`OUT`, chống trùng lặp giao dịch `IdempotencyKey`).
- **Phát sinh & Quản lý Cảnh báo (Alerts)**: Tự động tạo cảnh báo khi phát hiện bất thường (truy cập trái phép, nhiệt độ vượt ngưỡng) và chuyển tiếp tới **Notification Service**.
- **Lưu vết Kiểm toán (Audit & Decision Trail)**: Ghi nhận lịch sử quyết định để cung cấp dữ liệu phục vụ thống kê cho **Analytics Service**.

```mermaid
flowchart TD
    subgraph Upstream ["Upstream Data Providers"]
        IOT["IoT Ingestion Service<br/>(Telemetry Events)"]
        GATE["Access Gate Service<br/>(Card Swipe Events)"]
        VISION["AI Vision Service<br/>(Detection Events)"]
    end

    subgraph Core ["Core Business Service (team-core)"]
        direction TB
        API["FastAPI Backend (REST API)"]
        ENGINE["Policy & Decision Engine"]
        ALERT["Alert Management"]
        AUDIT["Audit & Decision Store"]
        
        API --> ENGINE
        ENGINE --> ALERT
        ENGINE --> AUDIT
    end

    subgraph Downstream ["Downstream Consumers"]
        NOTIFY["Notification Service<br/>(Alerts Dispatch)"]
        ANALYTICS["Analytics Service<br/>(Audit & Metrics)"]
    end

    IOT -->|POST /events| API
    GATE -->|POST /access/check| API
    VISION -->|POST /events| API
    
    ALERT -->|alert.created| NOTIFY
    AUDIT -->|decision.evaluated| ANALYTICS
```

---

## 2. Cấu trúc Repository & Quá trình Phát triển qua các Lab

Toàn bộ quá trình nghiên cứu, thiết kế hợp đồng, kiểm thử và đóng gói **Core Business Service** được phân bổ theo từng thư mục lab tương ứng:

```text
Core_Business_Service/
├── README.md                                    # [Tài liệu này] Tổng quan toàn bộ Service
│
├── FIT4110_Buoi01_Setup_ServiceBoundary/        # LAB 01: Thiết lập & Ranh giới Dịch vụ
│   ├── README.md                                # Hướng dẫn & tổng quan Buổi 1
│   ├── docs/service-boundary-guide.md           # Hướng dẫn xác định Service Boundary
│   ├── evidence/buoi-01/service-boundary.md     # Ranh giới nghiệp vụ chi tiết của Core Business
│   └── scripts/smoke_test.sh                    # Scripts smoke test môi trường ban đầu
│
├── FIT4110_lab02_openapi-main/                  # LAB 02: Thiết kế Hợp đồng OpenAPI 3.1.0
│   ├── README.md                                # Hướng dẫn thiết kế hợp đồng API
│   ├── campus-spectral.yaml                     # Bộ quy chuẩn kiểm tra hợp đồng Smart Campus
│   ├── docs/event-contract-*.md                 # Hợp đồng sự kiện với các bên liên quan
│   └── user-stories/                            # User stories và kịch bản đàm phán hợp đồng
│
├── FIT4110_lab03_postman_mock_testing-main/     # LAB 03: Postman, Mock Server & Newman CI
│   ├── README.md                                # Hướng dẫn thiết lập Mock và Test Suite
│   ├── contracts/core-business.openapi.yaml     # Hợp đồng OpenAPI hoàn chỉnh
│   ├── postman/collections/                     # Postman Test Collection (24 requests)
│   ├── postman/environments/                    # Postman Environments (Mock & Local)
│   └── reports/                                 # Báo cáo kết quả kiểm thử tự động
│
├── FIT4110_lab04_docker_packaging-main/         # LAB 04: Đóng gói Docker & Runtime Container
│   ├── Dockerfile                               # Multi-stage Dockerfile (Non-root, Healthcheck)
│   ├── .dockerignore                            # Tối ưu hóa build context
│   ├── .env.example                             # Cấu hình biến môi trường an toàn
│   ├── .spectral.yaml                           # Bộ quy chuẩn Spectral OAS 3.1
│   ├── Makefile                                 # Phím tắt thao tác nhanh
│   ├── RUN_LOCAL.md                             # Hướng dẫn chi tiết chạy cục bộ cho máy khác
│   ├── README.md                                # Tài liệu chi tiết Lab 04
│   ├── contracts/core-business.openapi.yaml     # Hợp đồng OpenAPI của Core Business
│   ├── src/core_app/main.py                     # Triển khai backend FastAPI đầy đủ
│   ├── postman/                                 # Bộ kiểm thử Postman/Newman trên Container
│   └── reports/                                 # Báo cáo JUnit XML & HTML Extra
│
└── FIT4110_lab05_docker_compose-main/          # LAB 05: Đa dịch vụ Docker Compose & Plug-a-thon (Final Stack)
    ├── docker-compose.yml                       # Stack Core API (:8001) + PostgreSQL (:5433) + 5 Mock Profiles
    ├── docker-compose.mock.yml                  # Override kết nối api với 5 mock services nội bộ (--profile mock)
    ├── Dockerfile / Dockerfile.mock             # Multi-stage non-root image cho Core & Mocks
    ├── .env.example                             # Cấu hình LAN / Storage Backend (postgres|memory) / Thresholds
    ├── src/core_app/main.py                     # Core Business API, Rule Engine, BackgroundTasks & Async Radar
    ├── src/core_app/storage.py                  # Dual Storage Abstraction (PostgresStore & InMemoryStore)
    ├── src/core_app/templates/dashboard.html    # Live Operations Dashboard (tải cấu hình động /integrations/config)
    ├── contracts/core-business.openapi.yaml     # Hợp đồng OpenAPI 3.1.0 đồng bộ với Lab 02
    ├── changelog.md                             # Nhật ký thay đổi v0.1.0 -> v0.5.0
    ├── endpoint_catalog.md                      # Danh mục toàn bộ API, Webhook, MQTT & Integrations
    ├── docs/architecture_one_pager.md           # Sơ đồ kiến trúc & luồng dữ liệu Core Business
    ├── checklists/readiness-checklist.md        # Danh sách kiểm tra sẵn sàng tích hợp
    ├── evidence/                                # Bằng chứng kiểm thử & log xác minh thực tế
    ├── reflection/                              # Đánh giá quyết định thiết kế & hướng phát triển
    ├── RUN_COMPOSE.md                           # Hướng dẫn chạy Mock Stack & LAN Plug-a-thon
    └── README.md                                # Tài liệu chi tiết Lab 05
```

### Tóm tắt tiến trình qua từng giai đoạn:

| Lab | Trọng tâm công việc của Core Business Service | Kết quả bàn giao chính |
|---|---|---|
| **Lab 01** | Xác định phạm vi trách nhiệm (In-scope/Out-of-scope), Actor, luồng dữ liệu Input/Output, Upstream/Downstream. | [service-boundary.md](file:///d:/Service/FIT4110_Buoi01_Setup_ServiceBoundary/evidence/buoi-01/service-boundary.md) |
| **Lab 02** | Chuẩn hóa API Contract theo chuẩn OpenAPI 3.1.0, định nghĩa mã lỗi RFC 9457 `ProblemDetails`, cơ chế Bearer Auth. | `core-business.openapi.yaml`, đàm phán hợp đồng đa bên |
| **Lab 03** | Xây dựng Prism Mock Server, thiết kế 24 kịch bản kiểm thử Postman bao phủ Functional, Auth, Negative, Boundary, SLA. | Postman Collection, Newman CI Reports (XML/HTML) |
| **Lab 04** | Triển khai mã nguồn FastAPI thực tế, đóng gói Multi-stage Dockerfile, chạy non-root `appuser`, native healthcheck, 100% không hardcode. | Container `fit4110/core-business:lab04`, 100% Test Pass |
| **Lab 05** | Đa dịch vụ Docker Compose + PostgreSQL/In-Memory Dual Storage, Mock Stack integration, Non-blocking MQTT/Notification, Demo Pack & Plug-a-thon LAN. | [docker-compose.yml](file:///d:/Service/FIT4110_lab05_docker_compose-main/docker-compose.yml), [RUN_COMPOSE.md](file:///d:/Service/FIT4110_lab05_docker_compose-main/RUN_COMPOSE.md) |

---

## 3. Danh mục API của Core Business Service

| Method | Endpoint | Mô tả Nghiệp vụ | Mã phản hồi |
|---|---|---|---|
| `GET` | `/health` | Kiểm tra trạng thái sẵn sàng của service và `storage` backend (`postgres` / `memory`). | `200 OK` |
| `POST` | `/alerts` | Tạo cảnh báo bất thường mới (Bearer `AUTH_TOKEN`), tự bắn MQTT & Notification nếu `HIGH/CRITICAL`. | `201 Created`, `401`, `422` |
| `GET` | `/alerts` | Lấy danh sách cảnh báo (phân trang `limit` từ 1 đến 100). | `200 OK`, `422` |
| `GET` | `/alerts/recent` | Lấy danh sách cảnh báo mới nhất của Smart Campus. | `200 OK` |
| `GET` | `/alerts/{alert_id}` | Tra cứu chi tiết một cảnh báo theo mã UUID. | `200 OK`, `404 Not Found` |
| `POST` | `/alerts/{alert_id}/resolve` | Chuyển cảnh báo sang `RESOLVED` và phát MQTT `business.alert.resolved`. | `200 OK`, `404 Not Found` |
| `POST` | `/access/check` | Đánh giá chính sách quẹt thẻ `POL-001` thời gian thực (kiểm tra cổng, khung giờ, trùng lặp `idempotencyKey`, rate-limit). | `200 OK`, `409 Conflict`, `422` |
| `GET` | `/policies/access/{id}` | Xem chi tiết chính sách kiểm soát ra/vào (`POL-001`). | `200 OK`, `404 Not Found` |
| `GET` | `/decisions/{id}` | Tra cứu lịch sử quyết định phục vụ kiểm toán. | `200 OK`, `404 Not Found` |
| `POST` | `/events` | Tiếp nhận sự kiện cảm biến IoT / hệ thống và tự sinh Alert khi quá ngưỡng. | `201 Created` |
| `POST` | `/vision/detection-result` | Webhook nhận kết quả phát hiện từ AI Vision Service và tự tạo Alert khi `risk_level` cao. | `200 OK`, `422` |
| `GET` | `/integrations/status` | Ping song song toàn bộ 5 service đối tác (AI Vision, IoT, Access Gate, Analytics, Notification). | `200 OK` |
| `POST` | `/integrations/notification/send` | Gửi thông báo cảnh báo trực tiếp qua Notification Service. | `200 OK` |

---

## 4. Hướng dẫn Khởi chạy & Kiểm thử Nhanh (Quick Start — Lab 05 & Lab 04)

### A. Chạy Stack Hoàn chỉnh Lab 05 (Docker Compose + PostgreSQL + 5 Mock Services)

```powershell
cd FIT4110_lab05_docker_compose-main
Copy-Item .env.example .env -ErrorAction SilentlyContinue
npm install

# Kiểm tra hợp đồng OpenAPI & cú pháp Docker Compose
npm run lint:openapi
npm run lint:compose

# Khởi chạy Core Business (:8001), PostgreSQL (:5433) và 5 Mock Services (:9001..9005)
docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock up -d --build --wait

# Kiểm tra /health & trạng thái tích hợp 5 đối tác
curl http://localhost:8001/health
curl http://localhost:8001/integrations/status

# Mở Live Operations Dashboard
Start-Process http://localhost:8001/dashboard

# Chạy kiểm thử tự động Newman (sinh reports/newman-lab05-compose.html & .xml)
npm run test:compose

# Dừng hệ thống
docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock down
```

> **Chuyển đổi kiểu lưu trữ (`Dual Storage`)**: Đặt `STORAGE_BACKEND=postgres` (PostgreSQL bền vững) hoặc `STORAGE_BACKEND=memory` (lưu tạm trên RAM) trong `.env`, hoặc mở comment tương ứng tại `create_store()` trong [storage.py](file:///d:/Service/FIT4110_lab05_docker_compose-main/src/core_app/storage.py).

> Xem thêm tài liệu Demo Pack Lab 05: [architecture_one_pager.md](file:///d:/Service/FIT4110_lab05_docker_compose-main/docs/architecture_one_pager.md) | [endpoint_catalog.md](file:///d:/Service/FIT4110_lab05_docker_compose-main/endpoint_catalog.md) | [changelog.md](file:///d:/Service/FIT4110_lab05_docker_compose-main/changelog.md) | [reflection/README.md](file:///d:/Service/FIT4110_lab05_docker_compose-main/reflection/README.md).

---

### B. Kiểm thử nhanh Container đơn lẻ Lab 04

Bất kỳ máy nào khi `git clone` repository này về đều có thể chạy và kiểm thử nhanh Lab 04 như sau:

### Bước 1: Di chuyển vào thư mục Lab 04 & Cài phụ thuộc test
```bash
cd FIT4110_lab04_docker_packaging-main
npm install
```

### Bước 2: Build Docker Image
```bash
docker build -t fit4110/core-business:lab04 .
```

### Bước 3: Khởi chạy Docker Container với cấu hình mặc định
```bash
docker run -d --rm   --name fit4110-core-lab04   -p 8000:8000   --env-file .env.example   fit4110/core-business:lab04
```

### Bước 4: Kiểm tra Healthcheck
```bash
curl http://localhost:8000/health
```
Phản hồi:
```json
{
  "status": "ok",
  "service": "core-business",
  "version": "0.4.0",
  "time": "2026-08-22T08:00:00Z"
}
```

### Bước 5: Chạy Bộ Kiểm thử Hợp đồng Tự động (Newman Test Suite)
```bash
npm run test:local
```
*(Kỳ vọng: 24/24 requests pass, 38/38 assertions pass, sinh báo cáo tại `reports/newman-lab04-local.html`)*

### Bước 6: Dừng Container
```bash
docker stop fit4110-core-lab04
```

---

## 5. Các Nguyên tắc Kỹ thuật & An ninh Đạt được

1. **Contract-First Design**: Mọi API và cấu trúc dữ liệu đều xuất phát từ hợp đồng chuẩn OpenAPI 3.1.0, tương thích RFC 9457 `ProblemDetails` (`application/problem+json`).
2. **Zero-Hardcode & Khả chuyển cao (Portability)**: Không sử dụng bất kỳ đường dẫn tuyệt đối hay IP tĩnh cục bộ nào. Mọi cấu hình (Host, Port, Token, Service Name, Version) đều nạp động qua biến môi trường.
3. **An toàn Container (Non-root Security)**: Container thực thi dưới user `appuser` (group `appgroup`), tuân thủ nguyên tắc đặc quyền tối thiểu.
4. **Giám sát Tự động (Native Healthcheck)**: Sử dụng chỉ thị `HEALTHCHECK` tích hợp của Docker định kỳ giám sát tính sẵn sàng của ứng dụng.
5. **Kiểm thử Toàn diện**: Bao phủ đầy đủ 6 nhóm kịch bản kiểm thử: Health, Functional Happy-path, Authentication, Negative Error Handling, Boundary Values, và SLA Performance (< 200ms).

---

## 6. Thông tin Tác giả & Nhóm Thực hiện

- **Học phần:** FIT4110 – Dịch vụ kết nối và Công nghệ nền tảng
- **Nhóm thực hiện:** Nhóm Core Business (`team-core`)
- **Hình ảnh Docker Tag:** `fit4110/core-business:lab04` | `v0.1.0-core-business`
