# Event Contract sơ bộ — Core Business → Notification Service

> File này ghi nhận thỏa thuận đã chốt giữa Core Business (Producer) và Notification Service (Consumer) cho cặp #4. Đặc tả AsyncAPI chuyển sang Lab 03.

## 1. Thông tin dependency

- Dependency số: #4
- Producer: Core Business
- Consumer: Notification Service
- Cơ chế: Queue async (RabbitMQ/Kafka)
- Event: `alert.created`, `alert.escalated`, `alert.resolved`
- Topic/Queue: `campus.alerts`
- Người ghi: Nhóm Core Business + Nhóm Notification
- Ngày: 2026-08-13 (cập nhật từ bản 2026-08-11)

## 2. Mục đích nghiệp vụ

Khi Core Business phát hiện sự kiện bất thường, Core tạo alert và publish event qua Queue. Notification Service consume event này để gửi thông báo đa kênh (Telegram, Email, Discord, SMS) đến người phụ trách.

- `alert.created` → Notification gửi cảnh báo mới
- `alert.escalated` → Notification gửi lại với mức độ cao hơn (leo thang)
- `alert.resolved` → Notification gửi tin nhắn báo đã xử lý xong

## 3. Event name / topic

| Event name | Mục đích |
|---|---|
| `alert.created` | Khi một cảnh báo mới được tạo |
| `alert.escalated` | Khi cảnh báo được leo thang (chưa xử lý sau thời gian quy định) |
| `alert.resolved` | Khi cảnh báo đã được giải quyết |

| Thành phần | Giá trị |
|---|---|
| Producer | Core Business |
| Consumer | Notification Service |
| Topic/Queue | `campus.alerts` |

> **Lưu ý**: Nhóm Notification sử dụng convention **snake_case** cho field name.

## 4. Payload tối thiểu

### 4.1. alert.created

```json
{
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "event_name": "alert.created",
  "correlationId": "req-0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
  "source": "core-business",
  "alert_id": "ALT-001",
  "severity": "high",
  "message": "Phát hiện người lạ khu vực máy chủ",
  "target_channels": ["telegram", "email"],
  "timestamp": "2026-08-13T08:00:00+07:00"
}
```

### 4.2. alert.escalated

```json
{
  "event_id": "123e4567-e89b-12d3-a456-426614174001",
  "event_name": "alert.escalated",
  "correlationId": "req-0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
  "source": "core-business",
  "alert_id": "ALT-001",
  "escalation_level": 2,
  "timestamp": "2026-08-13T08:40:00+07:00"
}
```

### 4.3. alert.resolved

```json
{
  "event_id": "123e4567-e89b-12d3-a456-426614174002",
  "event_name": "alert.resolved",
  "correlationId": "req-0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
  "source": "core-business",
  "alert_id": "ALT-001",
  "resolution_note": "Đội bảo vệ đã kiểm tra, là nhân viên IT quên thẻ.",
  "timestamp": "2026-08-13T09:00:00+07:00"
}
```

## 5. Ràng buộc đã chốt

| Vấn đề | Quyết định |
|---|---|
| `event_id` bắt buộc | ✅ Có — UUID, dùng làm idempotency key |
| `event_name` bắt buộc | ✅ Có |
| `correlationId` bắt buộc | ✅ Có — để trace xuyên service |
| `source` bắt buộc | ✅ Có — `core-business` |
| `timestamp` bắt buộc | ✅ Có — ISO 8601 |
| `severity` enum | `low`, `medium`, `high`, `critical` |
| Notification tự định tuyến kênh? | ✅ Có — dựa trên `severity`; `target_channels` là tùy chọn |
| Kênh hỗ trợ | `telegram`, `email`, `discord`, `sms` |
| Event có thể gửi trùng | Có — Notification idempotent theo `event_id` |
| Retry khi lỗi | 3 lần, interval 5s — chi tiết Lab 03 |
| Dead-letter queue | Có — chi tiết Lab 03 |
| Error response REST | Problem Details RFC 9457 (`application/problem+json`) |
| Field `error_detail` nullable | Dùng `type: [string, "null"]` (OpenAPI 3.1 chuẩn) |

## 6. Giao tiếp phụ (REST Sync fallback)

Notification Service cũng cung cấp REST endpoint cho mục đích test/debug:

| Method | Endpoint | Mục đích |
|---|---|---|
| `POST` | `/notifications` | Gửi thông báo thủ công (fallback/test) |
| `GET` | `/notifications` | Lấy log thông báo đã gửi (cho Analytics/Admin) |

## 7. Issue chuyển sang Lab 03

1. Đặc tả AsyncAPI cho topic `campus.alerts`
2. Cơ chế retry và dead-letter queue cụ thể
3. Schema validation cho message trên queue
4. Escalation policy: sau bao lâu chưa xử lý thì leo thang?
