# Event Contract sơ bộ — Core Business → Analytics Service

> File này ghi nhận thỏa thuận đã chốt giữa Core Business (Producer) và Analytics Service (Consumer) cho cặp #8. Đặc tả AsyncAPI chuyển sang Lab 03.

## 1. Thông tin dependency

- Dependency số: #8
- Producer: Core Business (Product B)
- Consumer: Analytics Service (Product A)
- Cơ chế: Message Queue / Event Bus
- Event: `business.alert.created`, `business.policy.decision.created`, `business.alert.resolved`
- Topic/Queue: `business.events`
- Người ghi: Nhóm Core Business + Nhóm Analytics Service
- Ngày: 2026-08-13 (cập nhật từ bản 2026-08-11)

## 2. Mục đích nghiệp vụ

Core Business publish event khi tạo cảnh báo, đưa ra quyết định policy, hoặc xử lý xong cảnh báo. Analytics Service consume cả 3 loại event để:

- Ghi nhận cảnh báo mới phát sinh
- Ghi nhận các quyết định policy ra/vào
- Ghi nhận cảnh báo đã được xử lý
- Tính KPI vận hành: số cảnh báo/ngày, thời gian xử lý trung bình, tỷ lệ ALLOW/DENY
- Kết hợp dữ liệu nghiệp vụ với dữ liệu IoT, Camera và Access Gate
- Cung cấp dữ liệu tổng hợp cho Dashboard

## 3. Event name / topic

| Event name | Topic/Queue | Mục đích |
|---|---|---|
| `business.alert.created` | `business.events` | Khi một cảnh báo mới được tạo |
| `business.policy.decision.created` | `business.events` | Khi Core kiểm tra policy và đưa ra quyết định |
| `business.alert.resolved` | `business.events` | Khi một cảnh báo đã được xử lý/giải quyết |

| Thành phần | Giá trị |
|---|---|
| Producer | Core Business |
| Consumer | Analytics Service |
| Topic/Queue | `business.events` |
| Số loại event | 3 |

> **Lưu ý**: Nhóm Analytics sử dụng convention **snake_case** cho field name trong phần `data`.

## 4. Payload tối thiểu

### 4.1. business.alert.created

```json
{
  "eventId": "880e8400-e29b-41d4-a716-446655440003",
  "eventType": "business.alert.created",
  "occurredAt": "2026-08-11T03:22:00Z",
  "correlationId": "af777173-b52e-74g7-d049-779988773333",
  "source": "core-business",
  "data": {
    "alert_id": "ALT-001",
    "alert_type": "CAPACITY_LIMIT",
    "location": "BUILDING-A",
    "severity": "MEDIUM",
    "created_at": "2026-08-11T03:22:00Z"
  }
}
```

### 4.2. business.policy.decision.created

```json
{
  "eventId": "990f9511-f30c-52e5-b827-668877664444",
  "eventType": "business.policy.decision.created",
  "occurredAt": "2026-08-11T03:23:10Z",
  "correlationId": "bf888284-c63f-85h8-e158-880099884444",
  "source": "core-business",
  "data": {
    "decision_id": "DEC-001",
    "policy_type": "ACCESS_POLICY",
    "decision": "ALLOW",
    "location": "GATE-01",
    "subject_type": "student",
    "decided_at": "2026-08-11T03:23:10Z"
  }
}
```

### 4.3. business.alert.resolved

```json
{
  "eventId": "aa0fa622-a41d-63f6-c938-779988775555",
  "eventType": "business.alert.resolved",
  "occurredAt": "2026-08-11T03:30:00Z",
  "correlationId": "cf999395-d74f-96i9-f269-991100995555",
  "source": "core-business",
  "data": {
    "alert_id": "ALT-001",
    "resolution_status": "RESOLVED",
    "resolved_by": "operator",
    "resolved_at": "2026-08-11T03:30:00Z"
  }
}
```

## 5. Ràng buộc đã chốt

| Vấn đề | Quyết định |
|---|---|
| `eventId` bắt buộc | ✅ Có — UUID |
| `eventType` bắt buộc | ✅ Có |
| `occurredAt` bắt buộc | ✅ Có — ISO 8601 UTC |
| `correlationId` bắt buộc | ✅ Có — để trace xuyên service |
| `source` bắt buộc | ✅ Có — `core-business` |
| `alert_id` bắt buộc | ✅ Có (cho alert.created và alert.resolved) |
| `decision_id` bắt buộc | ✅ Có (cho policy.decision.created) |
| `alert_type` bắt buộc | ✅ Có (cho alert.created) |
| `severity` bắt buộc | ✅ Có (cho alert.created) |
| `decision` bắt buộc | ✅ Có (cho policy.decision.created) |
| `resolution_status` bắt buộc | ✅ Có (cho alert.resolved) |
| Field naming trong `data` | snake_case |
| Event có thể gửi trùng | Có — Consumer phải idempotent theo `eventId` |
| Retry | Đặc tả tại Lab 03 |
| Dead-Letter Queue | Đặc tả tại Lab 03 |

## 6. Issue chuyển sang Lab 03

1. Đặc tả AsyncAPI cho topic `business.events`
2. Danh sách đầy đủ `alert_type` và `severity`
3. Schema AsyncAPI chi tiết
4. Retry policy và Dead-Letter Queue
5. Chính sách xử lý duplicate event
6. Analytics cần replay event cũ không? (event sourcing)
