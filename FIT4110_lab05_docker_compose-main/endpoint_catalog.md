# Endpoint Catalog — Core Business Service (`team-core`)

Danh mục đầy đủ toàn bộ HTTP REST APIs, Webhook, Integration Endpoints, Asynchronous MQTT Events và chuẩn lỗi RFC 9457 của **Core Business Service** (`contracts/core-business.openapi.yaml`).

---

## 1. Core Business API & Webhooks

| Nhóm | Method | Path | Auth | Mô tả nghiệp vụ | Mã trạng thái |
|---|---|---|---|---|---|
| **Health** | `GET` | `/health` | Public | Kiểm tra trạng thái sống của Core API & Storage backend (`postgres` / `memory`) | `200` |
| **Dashboard** | `GET` | `/` , `/dashboard` | Public | Giao diện Live Operations Dashboard HTML5 theo dõi 6 phân hệ | `200` |
| **Dashboard** | `POST` | `/dashboard/clear-data` | Public | Làm sạch bảng dữ liệu (`events`, `alerts`, `decisions`, `idempotency_keys`) trước khi demo | `200` |
| **Alerts** | `POST` | `/alerts` | `Bearer AUTH_TOKEN` | Tạo cảnh báo an ninh/vận hành mới; phát MQTT `business.alert.created` & đẩy Notification nếu `HIGH/CRITICAL` | `201`, `401`, `422`, `500` |
| **Alerts** | `GET` | `/alerts` | Optional Bearer | Liệt kê danh sách cảnh báo có phân trang (`limit` 1..100, trả `items`, `nextCursor`, `hasMore`, `total`) | `200`, `401`, `422` |
| **Alerts** | `GET` | `/alerts/recent` | Public | Lấy nhanh N cảnh báo gần nhất (mặc định `limit=5`) cho Dashboard/Analytics | `200` |
| **Alerts** | `GET` | `/alerts/{alert_id}` | Public | Xem chi tiết một cảnh báo theo UUID | `200`, `404` |
| **Alerts** | `POST` | `/alerts/{alert_id}/resolve` | Public | Đánh dấu cảnh báo `RESOLVED`, lưu `resolvedAt` & phát MQTT `business.alert.resolved` | `200`, `404` |
| **Access Policy** | `POST` | `/access/check` | Public (Gateway/Gate) | Đánh giá luật ra/vào `POL-001` (format thẻ, cổng cho phép, blacklist, timeWindow, rate-limit, idempotencyKey); SLA `< 200ms` | `200`, `409`, `422` |
| **Access Policy** | `GET` | `/policies/access/{policy_id}` | Public | Tra cứu thông tin chính sách truy cập (`POL-001`) | `200`, `404` |
| **Access Policy** | `GET` | `/decisions` | Public | Danh sách toàn bộ quyết định `ALLOW` / `DENY` đã đánh giá | `200` |
| **Access Policy** | `GET` | `/decisions/{decision_id}` | Public | Tra cứu chi tiết quyết định theo UUID phục vụ kiểm toán | `200`, `404` |
| **Events** | `POST` | `/events` | Public | Tiếp nhận sự kiện cảm biến IoT / hệ thống (`metric`/`value` hoặc phẳng `temperature`/`humidity`); tự sinh Alert nếu vượt ngưỡng | `201`, `422` |
| **Events** | `GET` | `/events` | Public | Danh sách sự kiện đã tiếp nhận (mới nhất đứng đầu) | `200` |
| **AI Vision Webhook** | `POST` | `/vision/detection-result` | Public | Nhận webhook kết quả AI Vision (`detection_id`, `camera_id`, `detections`, `risk_level`); tự sinh `UNKNOWN_PERSON` / `SUSPICIOUS_OBJECT` nếu risk cao | `200`, `422` |

---

## 2. Inter-Service Integration Endpoints (`/integrations/*`)

| Method | Path | Đối tác gọi tới | Mục đích |
|---|---|---|---|
| `GET` | `/integrations/config` | Internal config | Trả URL các đối tác, cấu hình MQTT và chế độ `storageBackend` cho Dashboard |
| `GET` | `/integrations/status` | Tất cả 5 đối tác | Ping song song `/health` của AI Vision, IoT, Access Gate, Analytics, Notification |
| `GET` | `/integrations/{service_name}/health` | 1 đối tác chỉ định | Ping trực tiếp `ai-vision`, `iot`, `gate`, `analytics`, hoặc `notification` |
| `GET` | `/integrations/gate/cards/{card_id}` | Access Gate (`GET /cards/{cardId}`) | Tra cứu thông tin chủ thẻ & trạng thái thẻ (gửi `GATE_AUTH_TOKEN`) |
| `GET` | `/integrations/gate/logs/recent` | Access Gate (`GET /access/logs/recent`) | Kéo log quẹt thẻ RFID gần nhất |
| `GET` | `/integrations/gate/gates/{gate_id}/status` | Access Gate (`GET /gates/{gateId}/status`) | Kiểm tra trạng thái đóng/mở barrier vật lý |
| `POST` | `/integrations/ai-vision/face-match` | AI Vision (`POST /vision/face-match`) | Gọi kiểm thử đối chiếu khuôn mặt |
| `GET` | `/integrations/ai-vision/models` | AI Vision (`GET /vision/models/info`) | Lấy danh sách model YOLO/Face đang nạp |
| `POST` | `/integrations/ai-vision/detect` | AI Vision (`POST /vision/detect`) | Gửi frame ảnh yêu cầu phát hiện đối tượng |
| `GET` | `/integrations/ai-vision/detections/{detection_id}` | AI Vision (`GET /vision/detections/{id}`) | Truy vấn chi tiết 1 lượt detection |
| `GET` | `/integrations/ai-vision/results/recent` | AI Vision (`GET /vision/results/recent`) | Lấy lịch sử kết quả AI Vision gần đây |
| `POST` | `/integrations/analytics/mqtt/publish` | MQTT Broker (`MQTT_BROKER_HOST:MQTT_BROKER_PORT`) | Phát sự kiện kiểm thử lên topic `business.events` |
| `POST` | `/integrations/notification/send` | Notification (`POST /notifications/send`) | Chuyển tiếp thông báo khẩn cấp (Email/SMS/Webhook) |

---

## 3. Asynchronous Events (MQTT Topic: `business.events`)

Core Business publish JSON envelope chuẩn về MQTT Broker cho phân hệ Analytics & Monitoring:

| `eventType` | Kích hoạt bởi | Các trường chính trong `data` |
|---|---|---|
| `business.alert.created` | `POST /alerts`, `POST /events` (vượt ngưỡng), `POST /vision/detection-result` (`HIGH/CRITICAL`), `POST /access/check` (`DENY`) | `alert_id`, `alert_type`, `location`, `severity`, `created_at` |
| `business.alert.resolved` | `POST /alerts/{alert_id}/resolve` | `alert_id`, `resolved_at` |
| `business.policy.decision.created` | `POST /access/check` | `decision_id`, `policy_type`, `decision`, `location`, `subject_type`, `decided_at`, `card_id`, `gate_id`, `direction`, `result` |

---

## 4. Chuẩn Lỗi & Tùy Chọn Lưu Trữ

- **Chuẩn lỗi RFC 9457 (`application/problem+json`)**: Mọi lỗi `401`, `404`, `409`, `422`, `500` trả về đồng nhất `{ type, title, status, detail, instance, errors? }`.
- **Dual Storage (`STORAGE_BACKEND`)**:
  - `postgres`: Lưu bền vững các bảng `alerts`, `policies`, `decisions`, `events`, `idempotency_keys` trên PostgreSQL 15 (`smartcampus-core-db`).
  - `memory`: Lưu tạm trong RAM qua Python dictionary/list (`InMemoryStore`) cho khởi chạy nhẹ hoặc test đơn vị độc lập.
