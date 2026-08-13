# Phân tích yêu cầu — vai Provider

- Cặp đàm phán: #10 (Access Gate → Core Business)
- Product: A / B
- Provider service: Core Business
- Consumer service: Access Gate
- Người viết: Nhóm Core Business
- Ngày: 2026-08-11

---

## 1. Resource chính

| Resource | Mô tả | Thuộc tính bắt buộc | Thuộc tính tùy chọn |
|---|---|---|---|
| `AccessDecision` | Kết quả kiểm tra policy ra/vào | `decisionId`, `cardId`, `gateId`, `result` (ALLOW/DENY), `reasonCode`, `evaluatedAt` | `policyId`, `expiresAt`, `note` |
| `AccessPolicy` | Rule/policy kiểm soát quyền truy cập | `policyId`, `name`, `effect` (ALLOW/DENY), `status` | `description`, `timeWindow`, `allowedGates` |

---

## 2. Action/API dự kiến

| Method | Path | Mục đích | Consumer gọi khi nào? |
|---|---|---|---|
| POST | `/access/check` | Kiểm tra policy ra/vào realtime | Mỗi lần có quẹt thẻ tại cổng, trước khi mở/đóng cổng |
| GET | `/policies/access/{policyId}` | Lấy chi tiết một policy | Khi Access Gate cần hiển thị lý do cho phép/từ chối |
| GET | `/decisions/{decisionId}` | Lấy lại kết quả quyết định đã xử lý | Khi cần audit hoặc tra cứu lịch sử quyết định |
| GET | `/health` | Kiểm tra Core Business còn hoạt động | Định kỳ hoặc trước khi gọi /access/check |

---

## 3. Error case

| Status | Tình huống | Response body dự kiến |
|---:|---|---|
| 400 | Payload `/access/check` thiếu `cardId` hoặc `gateId` | `Problem` với errors chỉ rõ field lỗi |
| 401 | Thiếu Bearer token | `Problem` |
| 403 | Token hợp lệ nhưng service không có quyền gọi endpoint | `Problem` |
| 404 | `policyId` hoặc `decisionId` không tồn tại | `Problem` |
| 422 | `cardId` đúng format nhưng không tồn tại trong hệ thống | `Problem` với detail giải thích |
| 500 | Rule engine lỗi nội bộ | `Problem` |

---

## 4. Giả định bổ sung

- Giả định 1: Response `/access/check` phải trả về trong ≤200ms để tránh kẹt cổng.
- Giả định 2: Khi Core Business lỗi hoặc timeout, Access Gate nên fail-closed (từ chối truy cập).
- Giả định 3: Mỗi lượt quẹt thẻ cần có `idempotencyKey` dạng UUID để tránh xử lý trùng.

---

## 5. Câu hỏi cho Consumer

1. Access Gate có cần nhận lại danh sách policy áp dụng trong response không, hay chỉ cần kết quả ALLOW/DENY?
2. Khi Core trả DENY, Access Gate có cần hiển thị `reasonCode` cho người quẹt thẻ không?
3. Access Gate có gọi `/access/check` cho cả chiều IN và OUT hay chỉ chiều IN?

---

## 6. Rủi ro tích hợp

| Rủi ro | Tác động | Đề xuất xử lý |
|---|---|---|
| Core Business timeout | Cổng kẹt, người dùng không vào được | SLA ≤200ms, Access Gate có fallback fail-closed |
| Field name không thống nhất (`card_id` vs `cardId`) | Consumer parse lỗi | Chốt camelCase trong `openapi.yaml` |
| Policy thay đổi nhưng Access Gate cache cũ | Quyết định sai | Không cache decision, luôn gọi realtime |
