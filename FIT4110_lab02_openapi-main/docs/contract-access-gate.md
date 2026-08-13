# Hợp đồng API chi tiết giữa Core Business ↔ Access Gate (Cặp #3 & #10)

> **Tài liệu đàm phán hợp đồng REST Sync** cho 2 cặp phụ thuộc giữa nhóm **Core Business** và nhóm **Access Gate**.

---

## 📌 Tổng quan quan hệ phụ thuộc

| Cặp | Vai trò Core Business | Vai trò Access Gate | Phương thức | Mục đích |
|---|---|---|---|---|
| **Cặp #10** | **Provider** (người cung cấp API) | **Consumer** (người gọi API) | REST sync | Access Gate gọi Core realtime để kiểm tra policy ra/vào (`POST /access/check`) trước khi mở cổng |
| **Cặp #3** | **Consumer** (người gọi API) | **Provider** (người cung cấp API) | REST sync | Core Business gọi Access Gate để tra cứu lịch sử log quẹt thẻ, trạng thái cổng và thông tin thẻ |

---

## 🛑 PHẦN 1: Cặp #10 — Access Gate gọi Core Business (Core là Provider)

### 1.1. Endpoint chính: `POST /access/check`
- **Mục đích**: Access Gate gửi thông tin quẹt thẻ, Core kiểm tra luật nghiệp vụ và trả về kết quả `ALLOW` hoặc `DENY`.
- **Cam kết SLA**: Phản hồi trong **≤ 200ms**.

#### Request Body (`application/json`):
```json
{
  "cardId": "RFID-2026-001",
  "gateId": "GATE-01",
  "direction": "IN",
  "idempotencyKey": "0196fb3d-4ad7-7d1e-9f49-aaa148d2b001",
  "timestamp": "2026-05-10T08:00:00Z"
}
```

| Field | Type | Bắt buộc | Mô tả & Ràng buộc |
|---|---|---|---|
| `cardId` | string | ✅ | Mã thẻ RFID, pattern: `^RFID-[0-9]{4}-[0-9]{3}$` |
| `gateId` | string | ✅ | Mã cổng quẹt thẻ, pattern: `^GATE-[0-9]{2}$` |
| `direction` | string (enum) | ✅ | Chiều di chuyển: `IN` (vào) hoặc `OUT` (ra) |
| `idempotencyKey` | string (UUID) | ✅ | Mã UUID duy nhất cho mỗi lượt quẹt để tránh xử lý trùng khi retry |
| `timestamp` | string (ISO 8601) | ✅ | Thời điểm quẹt thẻ tại cổng |

#### Response 200 OK — Thành công (`application/json`):
```json
{
  "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
  "cardId": "RFID-2026-001",
  "gateId": "GATE-01",
  "result": "ALLOW",
  "reasonCode": "VALID_CARD",
  "policyId": "POL-001",
  "evaluatedAt": "2026-05-10T08:00:00.120Z",
  "expiresAt": null
}
```

| Field | Type | Bắt buộc | Enum / Giá trị có thể |
|---|---|---|---|
| `decisionId` | string (UUID) | ✅ | ID định danh duy nhất cho quyết định xử lý này |
| `cardId` | string | ✅ | Mã thẻ đã kiểm tra |
| `gateId` | string | ✅ | Mã cổng |
| `result` | string (enum) | ✅ | `ALLOW` (mở cổng) hoặc `DENY` (chặn cổng) |
| `reasonCode` | string (enum) | ✅ | `VALID_CARD`, `EXPIRED_CARD`, `BLACKLISTED`, `OUTSIDE_TIME_WINDOW`, `UNKNOWN_CARD`, `POLICY_DENY` |
| `policyId` | string / null | ❌ | Mã policy áp dụng (ví dụ: `POL-001`), null nếu không khớp policy nào |
| `evaluatedAt` | string (ISO 8601) | ✅ | Thời điểm Core hoàn tất đánh giá |
| `expiresAt` | string / null | ❌ | Thời điểm quyết định hết hiệu lực (nếu có) |

---

### 1.2. Endpoint phụ trợ của Core
1. `GET /policies/access/{policyId}` — Lấy chi tiết thông tin policy kiểm soát ra/vào.
2. `GET /decisions/{decisionId}` — Tra cứu lại quyết định ra/vào đã đưa ra theo `decisionId`.
3. `GET /health` — Access Gate gọi kiểm tra trạng thái hoạt động của Core Business.

---

### 1.3. Xử lý lỗi & Trường hợp ngoại lệ (Error Handling)
Tất cả response lỗi đều theo chuẩn **RFC 9457 Problem Details** (`application/problem+json`):

| HTTP Status | Nguyên nhân | Phương án xử lý phía Access Gate |
|---:|---|---|
| **400 Bad Request** | Request thiếu field bắt buộc hoặc sai pattern `cardId`/`gateId` | Access Gate log lỗi, không mở cổng |
| **401 Unauthorized** | Thiếu Bearer Token hoặc token hết hạn | Access Gate kiểm tra lại cấu hình auth token |
| **409 Conflict** | Trùng `idempotencyKey` (lượt quẹt đã được xử lý trước đó) | Access Gate dùng lại kết quả `AccessDecision` trước |
| **422 Unprocessable** | Dữ liệu đúng định dạng nhưng thẻ bị hỏng/vô hiệu hóa | Access Gate hiển thị lý do lỗi lên màn hình cổng |
| **500 / Timeout** | Core lỗi nội bộ hoặc quá 200ms không trả lời | **Fail-closed**: Access Gate tự động **từ chối mở cổng** để đảm bảo an ninh |

---

## 🚪 PHẦN 2: Cặp #3 — Core Business gọi Access Gate (Core là Consumer)

Core Business cần gọi các API phía Access Gate để tra cứu thông tin và audit. Tất cả request đều gửi kèm header `Authorization: Bearer <JWT_TOKEN>`. Access Gate triển khai các endpoint sau:

| Method | Endpoint | Query Parameters | Mục đích Core gọi | Response kỳ vọng từ Access Gate |
|---|---|---|---|---|
| `GET` | `/access/logs/recent` | `startTime` (ISO 8601), `endTime` (ISO 8601), `limit` (default: 20, max: 100), `cursor` (string) | Core xem và audit các lượt quẹt thẻ theo khoảng thời gian | Mảng `AccessLog[]`, `nextCursor`, `hasMore` |
| `GET` | `/access/logs/{logId}` | Không | Core xem chi tiết 1 lượt quẹt thẻ cụ thể | Thông tin `AccessLog` chi tiết |
| `GET` | `/gates/{gateId}/status` | Không | Core kiểm tra trạng thái phần cứng cổng | `status`: `ONLINE`/`OFFLINE`/`LOCKED`/`MAINTENANCE` |
| `GET` | `/cards/{cardId}` | Không | Core tra thông tin chủ thẻ từ Access Gate | Thông tin `cardHolder`, `status` (`ACTIVE`/`BLOCKED`) |

---

## 💬 PHẦN 3: Kết quả đàm phán chính thức với nhóm Access Gate (Đã chốt)

Các nội dung đã chốt chính thức và ghi nhận vào `negotiation-log.md`:

1. **Về Timeout & Fallback policy** (Issue #2):
   - SLA: Response trong **≤ 200ms**.
   - Phía Access Gate xử lý **Fail-closed** (tự động đóng cổng khi lỗi/timeout) để đảm bảo an toàn an ninh.

2. **Về Naming Convention** (Issue #1):
   - Toàn bộ field JSON sử dụng chuẩn **camelCase** (`cardId`, `gateId`, `idempotencyKey`).

3. **Về Idempotency Key** (Issue #5):
   - Access Gate phát sinh mã UUID `idempotencyKey` cho mỗi lần quẹt thẻ gửi lên `POST /access/check` để tránh duplicate khi retry.

4. **Về Bảo mật API** (Issue #8):
   - Sử dụng header `Authorization: Bearer <JWT_TOKEN>` cho tất cả endpoint REST Sync giữa 2 service.

5. **Về Format Log, Filtering & Pagination** (Issue #9):
   - Endpoint `GET /access/logs/recent` hỗ trợ filter theo khoảng thời gian (`startTime`, `endTime`) và phân trang cursor-based (`limit`, `cursor`). Access Gate lưu log tối thiểu 30 ngày.
