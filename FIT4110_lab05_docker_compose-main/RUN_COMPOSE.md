# RUN_COMPOSE.md — Vận Hành Core Business Service (Smart Campus Operations Platform)

Tài liệu hướng dẫn triển khai **Core Business Service** và kết nối thời gian thực với các nhóm đối tác (**AI Vision**, **IoT Ingestion**, **Access Gate**, **Analytics**, **Notification**) trong mạng LAN.

---

## 1. Thông Tin Dịch Vụ & Container Chuẩn Toàn Dự Án

| Service | Tên Container Chuẩn | Port Trên Máy (Host) | Port Nội Bộ (Container) | Vai Trò Nghiệp Vụ |
|---|---|:---:|:---:|---|
| **Core Business API** | `smartcampus-core-service` | **`8001`** | `8000` | Nhận events/alerts, đánh giá chính sách ra vào |
| **PostgreSQL 15 DB** | `smartcampus-core-db` | **`5433`** | `5432` | Lưu trữ quyết định, chính sách, danh sách cảnh báo |

> **Cách đối tác trong mạng LAN kết nối đến Core:**
> - URL gốc: `http://<IP_MÁY_CORE>:8001`
> - Ví dụ: `http://192.168.137.25:8001/health`

---

## 2. Cấu Hình Địa Chỉ IP Các Nhóm Đối Tác (File `.env`)

Mở file `.env` và điền địa chỉ IPv4 máy tính của các nhóm bạn bè:

```env
# 1. Nhóm AI Vision (Nhận diện khuôn mặt)
AI_VISION_URL=http://192.168.137.1:8000

# 2. Nhóm IoT Ingestion (Cảm biến môi trường)
IOT_SERVICE_URL=http://192.168.137.10:8000

# 3. Nhóm Access Gate (Kiểm soát cổng barrier)
GATE_SERVICE_URL=http://192.168.137.20:8000

# 4. Nhóm Analytics (Thống kê và phân tích số liệu)
ANALYTICS_SERVICE_URL=http://192.168.137.30:8000

# 5. Nhóm Notification (Gửi cảnh báo Email/SMS/Push)
NOTIFICATION_SERVICE_URL=http://192.168.137.40:8000
```

---

## 3. Các Lệnh Vận Hành Nhanh

```powershell
# 1. Khởi động Stack Core Business (API + PostgreSQL)
docker compose up -d --build

# 2. Kiểm tra trạng thái kết nối tới TOÀN BỘ 5 đối tác trong mạng LAN
curl http://localhost:8001/integrations/status

# 3. Xem logs thời gian thực khi các nhóm gọi API sang Core
docker compose logs -f api

# 4. Chạy kiểm thử tự động Newman
npm run test:compose

# 5. Dừng hệ thống
docker compose down
```

---

## 4. API Endpoints Dành Cho Các Nhóm Gọi Sang Core Business

| Nhóm Gọi Sang | Method | Endpoint | Mục Đích |
|---|---|---|---|
| **Tất cả các nhóm** | `GET` | `/health` | Kiểm tra trạng thái sẵn sàng của Core |
| **Tất cả các nhóm** | `GET` | `/integrations/status` | Xem dashboard kiểm tra sức khoẻ toàn mạng LAN |
| **AI Vision / IoT** | `POST` | `/events` | Bắn sự kiện nhận diện khuôn mặt / đo nhiệt độ |
| **Tất cả các nhóm** | `POST` | `/alerts` | Báo cáo cảnh báo bất thường (Token: `mock-core-token-2026`) |
| **Access Gate** | `POST` | `/access/check` | Gửi mã thẻ RFID để Core quyết định cho phép vào hay không |
| **Analytics** | `GET` | `/alerts/recent` | Lấy danh sách 5 cảnh báo mới nhất phục vụ thống kê |
| **Analytics** | `GET` | `/decisions/{id}`| Tra cứu vết kiểm toán quyết định ra/vào |