# Event Contract sơ bộ — IoT Ingestion → Core Business

> File này ghi nhận thỏa thuận ban đầu cho cặp #5. Đặc tả AsyncAPI chuyển sang Lab 03.

## 1. Thông tin dependency

- Dependency số: #5
- Producer: IoT Ingestion
- Consumer: Core Business
- Cơ chế: Queue async
- Event/topic dự kiến: sensor.reading.created, sensor.threshold.exceeded
- Người ghi: Nhóm Core Business
- Ngày: 2026-08-11

## 2. Mục đích nghiệp vụ

IoT Ingestion publish event khi nhận dữ liệu cảm biến mới từ ESP32. Core Business consume event này để đánh giá policy (vượt ngưỡng nhiệt độ, phát hiện chuyển động bất thường) và quyết định có tạo alert hay không.

## 3. Event name / topic

| Mục | Giá trị |
|---|---|
| Event name | `sensor.reading.created`, `sensor.threshold.exceeded` |
| Topic/queue | `campus.sensors` |
| Producer | IoT Ingestion |
| Consumer | Core Business |

## 4. Payload — Mô tả chi tiết từng field

### 4.1. Envelope (metadata bắt buộc cho mọi event)

| Field | Type | Bắt buộc | Mô tả | Ví dụ |
|---|---|---|---|---|
| `eventId` | string (UUID) | ✅ | ID duy nhất của event, dùng để idempotency — Core sẽ bỏ qua nếu nhận trùng | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `eventType` | string (enum) | ✅ | Loại event: `sensor.reading.created` hoặc `sensor.threshold.exceeded` | `sensor.reading.created` |
| `occurredAt` | string (ISO 8601) | ✅ | Thời điểm phát sinh sự kiện — Core bỏ qua event trễ quá 5 phút | `2026-05-10T08:30:00Z` |
| `correlationId` | string (UUID) | ✅ | ID để trace xuyên service (sensor → Core → alert → notification) | `f1e2d3c4-b5a6-7890-abcd-ef1234567890` |
| `source` | string | ✅ | Tên service phát sự kiện | `iot-ingestion` |

### 4.2. Data (dữ liệu cảm biến)

| Field | Type | Bắt buộc | Mô tả | Ví dụ |
|---|---|---|---|---|
| `deviceId` | string | ✅ | Mã định danh thiết bị IoT, pattern: `SENSOR-NNN` | `SENSOR-001` |
| `metric` | string (enum) | ✅ | Loại chỉ số: `temperature`, `humidity`, `smoke`, `motion` | `temperature` |
| `value` | number | ✅ | Giá trị đo được — Core so sánh giá trị này với ngưỡng trong policy | `38.5` |
| `unit` | string | ✅ | Đơn vị đo: `celsius`, `percent`, `boolean`, `ppm` | `celsius` |
| `locationId` | string | ✅ | Khu vực đặt sensor — Core dùng để áp rule theo vùng | `room-a101` |

### 4.3. Payload mẫu hoàn chỉnh

```json
{
  "eventId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "eventType": "sensor.reading.created",
  "occurredAt": "2026-05-10T08:30:00Z",
  "correlationId": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
  "source": "iot-ingestion",
  "data": {
    "deviceId": "SENSOR-001",
    "metric": "temperature",
    "value": 38.5,
    "unit": "celsius",
    "locationId": "room-a101"
  }
}
```

### 4.4. Payload mẫu — sensor.threshold.exceeded

```json
{
  "eventId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "eventType": "sensor.threshold.exceeded",
  "occurredAt": "2026-05-10T08:31:00Z",
  "correlationId": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
  "source": "iot-ingestion",
  "data": {
    "deviceId": "SENSOR-001",
    "metric": "temperature",
    "value": 45.2,
    "unit": "celsius",
    "locationId": "room-a101"
  }
}
```

## 5. Quy tắc đơn vị (unit) theo loại metric

| metric | unit | Khoảng giá trị hợp lệ |
|---|---|---|
| `temperature` | `celsius` | -40 đến 100 |
| `humidity` | `percent` | 0 đến 100 |
| `smoke` | `ppm` | 0 đến 10000 |
| `motion` | `boolean` | 0 (không) hoặc 1 (có) |

## 6. Ràng buộc cần thống nhất

| Vấn đề | Quyết định tạm thời |
|---|---|
| `eventId` có bắt buộc không? | ✅ Có — UUID v4, Core kiểm tra trùng |
| `correlationId` có bắt buộc không? | ✅ Có — để trace toàn luồng |
| `timestamp` có bắt buộc không? | ✅ Có — Core bỏ qua event trễ > 5 phút |
| Đơn vị sensor dùng gì? | celsius, percent, ppm, boolean (xem bảng trên) |
| `locationId` có bắt buộc không? | ✅ Có — Core cần biết khu vực để áp rule |
| `deviceId` pattern? | `SENSOR-NNN` (3 chữ số) |
| IoT có được gửi trùng event không? | Có thể — Core phải idempotent theo `eventId` |
| Core bỏ qua event trễ quá bao lâu? | > 5 phút — log warning, không xử lý |
| Retry khi lỗi | IoT retry 3 lần, interval 2s — chi tiết Lab 03 |

## 7. Issue chuyển sang Lab 03

1. Đặc tả AsyncAPI cho topic `campus.sensors`
2. Batching: IoT có thể gửi nhiều reading trong 1 message không?
3. Rate limiting khi sensor gửi quá nhiều event/s
4. Dead-letter queue cho event Core không xử lý được
