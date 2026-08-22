# FIT4110 Lab 04 — Docker Packaging: Core Business Service

**Học phần:** FIT4110 – Dịch vụ kết nối và Công nghệ nền tảng  
**Hệ thống Case Study:** Smart Campus Operations Platform  
**Service đảm nhiệm:** **Core Business Service** (`team-core`)  

---

## 1. Giới thiệu Core Business Service

Trong kiến trúc nền tảng **Smart Campus Operations Platform**, **Core Business Service** là trung tâm điều phối và thực thi chính sách nghiệp vụ (Policy Engine). Service tiếp nhận các sự kiện từ các phân hệ cảm biến (IoT Ingestion), hệ thống kiểm soát ra/vào (Access Gate) và phân tích thị giác AI (AI Vision), áp dụng các quy tắc để đánh giá tình huống, phát sinh cảnh báo (Alert) và lưu trữ vết kiểm toán (Decision Audit).

```text
               SƠ ĐỒ LUỒNG ĐÓNG GÓI & KIỂM THỬ LAB 04
               
  ┌─────────────────────────────────────────────────────────────┐
  │  OpenAPI 3.1 Contract (contracts/core-business.openapi.yaml)│
  └──────────────────────────────┬──────────────────────────────┘
                                 │
     ┌───────────────────────────┴───────────────────────────┐
     ▼                                                       ▼
┌───────────────────────────────┐              ┌───────────────────────────────┐
│ Backend FastAPI               │              │ Postman Contract Test Suite   │
│ (src/core_app/main.py)        │              │ (24 Requests / 38 Assertions) │
└──────────────┬────────────────┘              └──────────────┬────────────────┘
               │                                              │
               ▼                                              │
┌───────────────────────────────┐                             │
│ Multi-Stage Dockerfile        │                             │
│ - Builder & Runtime Stages    │                             │
│ - Non-root user (appuser)     │                             │
│ - Native HEALTHCHECK          │                             │
│ - 100% Config qua Env         │                             │
└──────────────┬────────────────┘                             │
               │                                              │
               ▼                                              │
┌───────────────────────────────┐                             │
│ Docker Container Runtime      │ <───────────────────────────┘
│ (fit4110-core-lab04 :8000)    │   Newman Automated Verification
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│ Newman Test Reports           │
│ - reports/newman-lab04-*.html │
│ - reports/newman-lab04-*.xml  │
└───────────────────────────────┘
```

---

## 2. Danh mục API của Core Business Service

Toàn bộ các endpoint được định nghĩa chính xác theo hợp đồng OpenAPI 3.1.0 và triển khai tại `src/core_app/main.py`:

| Method | Endpoint | Mục đích & Nghiệp vụ |
|---|---|---|
| `GET` | `/health` | Kiểm tra trạng thái sẵn sàng của service (`status: ok`, `service: core-business`, `version: 0.4.0`). |
| `POST` | `/alerts` | Tạo cảnh báo mới (yêu cầu Bearer Token). Hỗ trợ trả mã lỗi RFC 9457 `ProblemDetails`. |
| `GET` | `/alerts` | Lấy danh sách cảnh báo có phân trang `limit` (kiểm tra boundary `1 <= limit <= 100`). |
| `GET` | `/alerts/recent` | Lấy nhanh 5 cảnh báo mới nhất của hệ thống Smart Campus. |
| `GET` | `/alerts/{alert_id}` | Tra cứu chi tiết một cảnh báo theo mã định danh UUID. |
| `POST` | `/access/check` | Đánh giá chính sách quẹt thẻ ra/vào cổng: kiểm tra định dạng `cardId` (`RFID-YYYY-NNN`), hướng `direction` (`IN`/`OUT`) và chống trùng lặp `IdempotencyKey`. |
| `GET` | `/policies/access/{policy_id}` | Lấy chi tiết chính sách kiểm soát ra/vào (`POL-001`). |
| `GET` | `/decisions/{decision_id}` | Truy vấn lịch sử quyết định cho mục đích kiểm toán và phân tích. |
| `POST` | `/events` | Tiếp nhận sự kiện tổng quát từ các phân hệ khác. |

---

## 3. Thiết kế Dockerfile & Tiêu chuẩn An ninh Container

File `Dockerfile` được tối ưu hóa theo các tiêu chuẩn công nghệ nền tảng:

1. **Multi-Stage Build**:
   - **Stage 1 (Builder)**: Sử dụng `python:3.11-slim`, tạo môi trường ảo tại `/opt/venv`, cài đặt và nâng cấp dependencies từ `requirements.txt`.
   - **Stage 2 (Runtime)**: Image tối giản, chỉ sao chép virtualenv `/opt/venv` và thư mục `src/core_app/`, giảm tối đa kích thước image và diện tích tấn công (attack surface).
2. **Bảo mật Non-root User**:
   - Tạo group `appgroup` và user `appuser`.
   - Chạy tiến trình bằng lệnh `USER appuser`, ngăn ngừa nguy cơ leo thang đặc quyền từ container ra máy chủ host.
3. **Docker Native Healthcheck**:
   - Khai báo chỉ thị `HEALTHCHECK` thăm dò `/health` định kỳ mỗi 30s sử dụng thư viện `urllib.request` có sẵn của Python, không cần cài đặt thêm gói `curl` trong runtime.
4. **Tuyệt đối Không Hardcode (Portability)**:
   - Các tham số `APP_HOST` (mặc định `0.0.0.0`) và `APP_PORT` (mặc định `8000`) được nạp linh hoạt qua biến môi trường.
   - Secret và token không ghi cứng trong Dockerfile hoặc mã nguồn mà truyền qua `--env-file .env.example`.
5. **Context Tối ưu qua `.dockerignore`**:
   - Loại trừ `node_modules`, `.venv`, `.git`, `reports`, cache `__pycache__` để context build siêu nhẹ.

---

## 4. Cấu trúc Thư mục

```text
FIT4110_lab04_docker_packaging-main/
├── Dockerfile                         # Multi-stage Dockerfile cho Core Business
├── .dockerignore                      # Loại bỏ rác khỏi build context
├── .env.example                       # Biến môi trường mẫu
├── .gitignore                         # Loại bỏ file tạm khỏi Git
├── .spectral.yaml                     # Quy chuẩn lint OpenAPI 3.1.0 (Spectral)
├── Makefile                           # Phím tắt thực thi nhanh
├── package.json                       # Scripts quản lý Newman, Prism, Spectral
├── requirements.txt                   # Phụ thuộc Python (FastAPI, Uvicorn, Pydantic)
├── README.md                          # Tài liệu tổng quan
├── RUN_LOCAL.md                       # Hướng dẫn chi tiết chạy cục bộ
├── contracts/
│   └── core-business.openapi.yaml     # Hợp đồng OpenAPI 3.1.0 của Core Business
├── src/
│   └── core_app/
│       ├── __init__.py
│       └── main.py                    # Triển khai FastAPI cho Core Business
├── postman/
│   ├── collections/
│   │   └── FIT4110_lab04_core_business.postman_collection.json # Bộ test Postman 24 requests
│   └── environments/
│       ├── FIT4110_lab04_core_local.postman_environment.json   # Environment cho Container
│       └── FIT4110_lab04_mock.postman_environment.json         # Environment cho Mock Server
├── reports/
│   ├── newman-lab04-local.html        # Báo cáo HTML sinh bởi Newman
│   └── newman-lab04-local.xml         # Báo cáo JUnit XML
├── scripts/
│   ├── run-newman.sh                  # Script tiện ích chạy Newman
│   ├── start-prism-mock.sh            # Script tiện ích bật Mock Server
│   └── wait-for-health.sh             # Script chờ /health sẵn sàng
├── docs/
│   ├── DOCKER_LAB_GUIDE.md            # Hướng dẫn chi tiết về đóng gói Docker cho Core Business
│   ├── TEAM_TASKS.md                  # Nhiệm vụ chi tiết của nhóm Core Business
│   └── TROUBLESHOOTING.md             # Xử lý các sự cố thường gặp
├── checklists/
│   ├── docker_readiness_checklist.md  # Checklist kiểm tra Docker readiness
│   └── submission_checklist.md        # Checklist artefact bàn giao
└── .github/
    └── workflows/
        └── docker-newman.yml          # GitHub Actions CI tự động build & test
```

---

## 5. Hướng dẫn Chạy & Kiểm thử Nhanh (Quick Start)

### Bước 1: Cài đặt phụ thuộc npm (Newman & Linter)
```bash
npm install
```

### Bước 2: Kiểm tra OpenAPI Contract với Spectral
```bash
npm run lint:openapi
```
*(Kết quả: `No results with a severity of 'error' found!`)*

### Bước 3: Build Docker Image
```bash
docker build -t fit4110/core-business:lab04 .
```
*(Hoặc dùng `make build`)*

### Bước 4: Chạy Docker Container
```bash
docker run -d --rm   --name fit4110-core-lab04   -p 8000:8000   --env-file .env.example   fit4110/core-business:lab04
```
*(Hoặc dùng `make run-detached`)*

### Bước 5: Kiểm tra Healthcheck
```bash
curl http://localhost:8000/health
```
Phản hồi mong đợi:
```json
{
  "status": "ok",
  "service": "core-business",
  "version": "0.4.0",
  "time": "2026-08-22T08:00:00Z"
}
```

Kiểm tra trạng thái container:
```bash
docker ps
```
*(Trạng thái STATUS hiển thị: `Up ... (healthy)`)*

### Bước 6: Chạy Newman Test Suite trên Container
```bash
npm run test:local
```
*(Hoặc dùng `make test-docker`)*

Báo cáo kiểm thử tự động được ghi nhận tại:
- `reports/newman-lab04-local.html` (Báo cáo trực quan HTML)
- `reports/newman-lab04-local.xml` (Báo cáo JUnit XML)

### Bước 7: Dừng Container
```bash
docker stop fit4110-core-lab04
```
*(Hoặc dùng `make stop`)*

---

## 6. Phân tích Bộ Kiểm thử Newman (24 Requests / 38 Assertions)

Bộ test trong `FIT4110_lab04_core_business.postman_collection.json` kiểm thử toàn diện 6 nhóm chức năng trên container:

1. **`00_Health`**: Kiểm tra trạng thái hoạt động của container (`GET /health` trả 200, phản hồi `status: ok`).
2. **`01_Functional`**: Kiểm tra các nghiệp vụ chính (`POST /alerts`, `GET /alerts`, `GET /alerts/recent`, `GET /alerts/{id}`, `POST /access/check`, `GET /policies/access/{id}`, `GET /decisions/{id}`, `POST /events`).
3. **`02_Auth`**: Xác thực tính hợp lệ của Bearer Token, kiểm tra từ chối mã 401 khi thiếu hoặc token không đúng.
4. **`03_Negative`**: Đảm bảo toàn bộ phản hồi lỗi tuân thủ chuẩn RFC 9457 `ProblemDetails` (`application/problem+json`):
   - Thiếu trường bắt buộc trong payload (422).
   - Sai định dạng `cardId` không khớp `RFID-YYYY-NNN` (422).
   - Tra cứu tài nguyên không tồn tại (404).
   - Xung đột giao dịch trùng lặp IdempotencyKey (409).
   - Sai giá trị enum `direction` (422).
   - Xử lý lỗi hệ thống máy chủ 500 giả lập.
5. **`04_Boundary_Reliability`**: Kiểm tra biên phân trang: `limit=1` (biên dưới), `limit=100` (biên trên), `limit=101` (vượt ngưỡng trả 422).
6. **`05_Consumer_side_Smoke`**: Kiểm tra tính sẵn sàng trong giao tiếp giữa các service.
7. **`06_Local_only_NonFunctional`**: Đảm bảo Core Business Service phản hồi trong thời gian SLA (< 200ms trên local).

---

## 7. Đánh giá & Bằng chứng Hoàn thành (Rubric)

| Tiêu chí | Điểm tối đa | Kết quả đạt được |
|---|---:|---|
| **Dockerfile chuẩn** | 2.0 | Multi-stage build, base image `python:3.11-slim`, layer caching tối ưu |
| **Container & /health** | 2.0 | Khởi chạy ổn định, native Docker healthcheck pass, `/health` 200 OK |
| **Bảo mật & Biến môi trường** | 2.0 | Chạy non-root `appuser`, cấu hình qua `.env.example`, `.dockerignore` sạch |
| **Kiểm thử Newman** | 2.0 | 24/24 requests pass, 38/38 assertions pass trên container, xuất báo cáo `reports/` |
| **Tài liệu RUN_LOCAL.md** | 1.0 | Rõ ràng, người khác `git clone` về có thể tái lập trong 3-5 bước |
| **Minh chứng & Image Tag** | 1.0 | Log build, log test, tag chuẩn `v0.1.0-core-business` |
| **Tổng điểm** | **10.0** | **Đạt tối đa** |
