# Biên bản đàm phán hợp đồng API

- Cặp đàm phán: #2, #3, #10 (REST sync) và #4, #5, #8 (Queue async)
- Product: A / B
- Provider: Core Business (cặp #10), AI Vision (cặp #2), Access Gate (cặp #3)
- Consumer: Core Business (cặp #2, #3), Access Gate (cặp #10)
- Phiên: v1.0
- Ngày: 2026-08-11

---

## Issue #1 — Format field name

- Raised by: Consumer (Core Business)
- Endpoint: Tất cả endpoint
- Concern: Các nhóm có thể dùng khác nhau: `card_id` vs `cardId` vs `CardId`
- Proposal: Toàn bộ API dùng **camelCase** cho field name
- Resolution: Modified — camelCase cho Core Business, Access Gate, IoT. **Ngoại lệ: AI Vision giữ snake_case** theo convention Python/ML của họ
- Rationale: AI Vision dùng Python + FastAPI (convention snake_case), ép đổi camelCase gây thêm adapter layer không cần thiết. Core Business chấp nhận parse snake_case khi gọi AI Vision
- Impact: Core Business cần mapping snake_case ↔ camelCase khi tích hợp AI Vision

---

## Issue #2 — Timeout SLA cho /access/check

- Raised by: Consumer (Access Gate)
- Endpoint: `POST /access/check`
- Concern: Nếu Core Business xử lý chậm, cổng sẽ kẹt và người dùng phải chờ
- Proposal: Core Business cam kết response trong ≤200ms; nếu timeout thì Access Gate fail-closed (từ chối)
- Resolution: Accepted
- Rationale: Cổng ra/vào cần phản hồi nhanh, fail-closed an toàn hơn fail-open
- Impact: Core Business cần tối ưu Rule Engine; Access Gate cần implement timeout handler

---

## Issue #3 — Ngưỡng confidence cho AI Vision

- Raised by: Consumer (Core Business)
- Endpoint: `POST /vision/face-match`, `GET /vision/detections/{detectionId}`
- Concern: Core Business cần biết confidence bao nhiêu thì coi là match để tạo alert
- Proposal: confidence ≥ 0.85 → match, 0.5–0.85 → uncertain (cần review thủ công), < 0.5 → no match
- Resolution: Modified — AI Vision trả confidence và riskLevel, Core tự quyết định ngưỡng
- Rationale: Ngưỡng là business rule thuộc Core, AI Vision chỉ cung cấp dữ liệu thô
- Impact: Schema `Detection` cần có cả `confidence` (number) và `riskLevel` (enum: low/medium/high)

---

## Issue #4 — Error response format thống nhất

- Raised by: Provider (Core Business)
- Endpoint: Tất cả endpoint trả lỗi
- Concern: Mỗi nhóm có thể trả error JSON khác nhau, Consumer khó parse
- Proposal: Tất cả response lỗi 4xx/5xx dùng **Problem Details (RFC 9457)** với content-type `application/problem+json`
- Resolution: Accepted
- Rationale: Chuẩn industry, có `type`, `title`, `status`, `detail`, `errors[]` — đủ thông tin debug
- Impact: Mỗi service cần implement Problem schema trong `components/schemas`

---

## Issue #5 — Idempotency key cho /access/check

- Raised by: Provider (Core Business)
- Endpoint: `POST /access/check`
- Concern: Nếu Access Gate retry do timeout, Core có thể xử lý trùng cùng một lượt quẹt thẻ
- Proposal: Access Gate gửi `idempotencyKey` (UUID) trong request body; Core kiểm tra trùng trước khi evaluate
- Resolution: Accepted
- Rationale: Tránh tạo nhiều decision cho cùng một lượt quẹt, đảm bảo dữ liệu audit chính xác
- Impact: Thêm field `idempotencyKey` vào schema `AccessCheckRequest`; Core trả 409 Conflict nếu trùng

---

## Issue #6 — Event async: payload tối thiểu cho alert.created

- Raised by: Consumer (Notification)
- Endpoint: Event `alert.created` (cặp #4 async)
- Concern: Notification cần biết gửi qua kênh nào, nội dung gì, mức độ ra sao
- Proposal: Payload gồm: `alertId`, `type`, `severity`, `message`, `target`, `timestamp`, `correlationId`
- Resolution: Accepted
- Rationale: Notification cần `severity` để ưu tiên kênh (HIGH → Telegram, LOW → email); `target` để routing
- Impact: Core Business phải include đầy đủ field khi publish event; chi tiết AsyncAPI chuyển Lab 03

---

## Issue #7 — Event async: envelope metadata naming cho IoT event

- Raised by: Producer (IoT Ingestion)
- Endpoint: Event `sensor.reading.created` (cặp #5 async)
- Concern: IoT Ingestion muốn thống nhất field timestamp envelope dùng `occurredAt` thay cho `timestamp`, và bổ sung cố định `source = "iot-ingestion"`
- Proposal: Thống nhất envelope chuẩn gồm: `eventId`, `eventType`, `occurredAt`, `correlationId`, `source`
- Resolution: Accepted
- Rationale: `occurredAt` là chuẩn Event-Driven Architecture (EDA) phản ánh thời điểm đo thô tại sensor; `source` hỗ trợ routing/filter event
- Impact: Core Business cập nhật contract `event-contract-05-iot-core.md` dùng `occurredAt` và `source`

---

## Issue #8 — Cơ chế bảo mật và Authorization Header cho REST Sync

- Raised by: Consumer (Access Gate) / Provider (Core Business)
- Endpoint: Tất cả REST sync endpoints (`POST /access/check`, `GET /access/logs/recent`, ...)
- Concern: Cần thống nhất cơ chế xác thực và truyền token khi gọi API giữa 2 service
- Proposal: Sử dụng **HTTP Bearer Token** với chuẩn JWT (`Authorization: Bearer <JWT_TOKEN>`) như đã khai báo trong `components/securitySchemes`
- Resolution: Accepted
- Rationale: Đảm bảo tính xác thực, phân quyền giữa các service và dễ dàng mock trên Prism
- Impact: Mọi request REST sync bắt buộc truyền header `Authorization: Bearer <token>`

---

## Issue #9 — Lọc theo thời gian và Phân trang (Pagination & Filter) cho Access Log

- Raised by: Consumer (Core Business) / Provider (Access Gate)
- Endpoint: `GET /access/logs/recent` (cặp #3)
- Concern: Core Business cần query log quẹt thẻ theo khoảng thời gian và tránh tải quá nhiều dữ liệu một lúc
- Proposal: 
  - Hỗ trợ query params: `startTime` (ISO 8601), `endTime` (ISO 8601)
  - Hỗ trợ phân trang: `limit` (default: 20, max: 100), `cursor` (cursor-based pagination)
- Resolution: Accepted
- Rationale: Giúp Core Business audit dữ liệu linh hoạt mà không gây quá tải mạng hay cơ sở dữ liệu phía Access Gate
- Impact: Access Gate triển khai `startTime`, `endTime`, `limit`, `cursor` trên endpoint `GET /access/logs/recent`

---

## Issue #10 — Event async: chốt event name, topic và payload cho Core → Analytics

- Raised by: Consumer (Analytics Service) / Producer (Core Business)
- Endpoint: Event `business.alert.created`, `business.policy.decision.created`, `business.alert.resolved` (cặp #8 async)
- Concern: Cần thống nhất tên event, topic, và cấu trúc payload giữa 2 bên
- Proposal:
  - Event name dùng prefix `business.` thay vì không có prefix: `business.alert.created`, `business.policy.decision.created`, `business.alert.resolved`
  - Topic: `business.events` (thay vì `campus.decisions`)
  - Data fields dùng **snake_case** theo convention của Analytics (Python)
  - Analytics cần nhận cả 3 event để theo dõi đầy đủ vòng đời cảnh báo
- Resolution: Accepted
- Rationale: Prefix `business.` giúp phân biệt event nghiệp vụ với event kỹ thuật; Analytics dùng Python nên snake_case hợp lý hơn; 3 event cho phép Analytics tính KPI đầy đủ
- Impact: Core Business cập nhật `event-contract-08-core-analytics.md` theo cấu trúc mới; chi tiết AsyncAPI chuyển Lab 03

---

## Issue #11 — Event async: chốt envelope và chuẩn hóa với Notification Service

- Raised by: Producer (Core Business)
- Endpoint: Event `alert.created`, `alert.escalated`, `alert.resolved` (cặp #4 async)
- Concern: Bản đầu tiên của Notification thiếu `correlationId` và `source` trong event envelope, dùng `nullable: true` thay vì union type, và error response không theo Problem Details
- Proposal:
  - Bổ sung `correlationId` (UUID) và `source: "core-business"` vào cả 3 event schema
  - Đổi `nullable: true` thành `type: [string, "null"]` theo OpenAPI 3.1 / Spectral rule `campus-no-nullable`
  - Error response dùng chuẩn RFC 9457 Problem Details (`application/problem+json`)
- Resolution: Accepted — Notification Service đã sửa cả 3 điểm trong bản v0.3.0
- Rationale: Đảm bảo trace xuyên service, tuân thủ Spectral lint, và đồng bộ error format toàn hệ thống
- Impact: Notification cập nhật openapi.yaml v0.3.0; Core Business cập nhật `event-contract-04-core-notification.md`

---

# Chốt hợp đồng v1.0

Provider sign-off: Nhóm Core Business _______________
Consumer sign-off: Nhóm Access Gate / AI Vision _______________
Witness (GV/TA):    _______________
Date:               2026-08-__

---

## Ghi chú warning nếu Spectral còn cảnh báo

| Warning | Lý do chấp nhận tạm thời | Kế hoạch sửa |
|---|---|---|
| Chưa có AsyncAPI cho cặp async | Lab 02 chỉ yêu cầu ghi nhận event contract sơ bộ | Viết AsyncAPI đầy đủ ở Lab 03 |
