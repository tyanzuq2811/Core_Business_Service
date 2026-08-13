# FIT4110 Lab 03 — Báo Cáo Kiểm Thử Hợp Đồng API (Core Business Service)

**Thông tin chung:**
- **Service**: Core Business Service
- **Nhóm thực hiện**: Nhóm Core Business
- **Công cụ kiểm thử**: Postman, Prism Mock Server, Newman CLI
- **Môi trường test**: Mock Server (`http://localhost:4010`) & Local Environment (`http://localhost:8000`)
- **Tệp hợp đồng gốc**: `contracts/core-business.openapi.yaml`

---

## 📊 Bảng Tổng Hợp Test Case & Kết Quả Execution (Ref. Run)

| ID / Folder | Method | Endpoint | Scenario | Expected / assertion chính | Ref. run |
|---|---|---|---|---|---|
| **CORE-01**<br>`00_Health` | `GET` | `/health` | Service alive | `200; status=ok` | **PASS** |
| **CORE-02**<br>`01_Functional` | `POST` | `/alerts` | Tạo cảnh báo mới (Happy path) | `201; id, status=OPEN` | **PASS** |
| **CORE-03**<br>`01_Functional` | `GET` | `/alerts` | Lấy danh sách cảnh báo phân trang | `200; items array, hasMore` | **PASS** |
| **CORE-04**<br>`01_Functional` | `GET` | `/alerts/recent` | Lấy các cảnh báo gần đây | `200; items array` | **PASS** |
| **CORE-05**<br>`01_Functional` | `GET` | `/alerts/{alertId}` | Chi tiết cảnh báo theo UUID | `200; alert object` | **PASS** |
| **CORE-06**<br>`01_Functional` | `POST` | `/access/check` | Kiểm tra policy ra/vào realtime | `200; decisionId, ALLOW/DENY` | **PASS** |
| **CORE-07**<br>`01_Functional` | `GET` | `/policies/access/{policyId}` | Chi tiết access policy | `200; policyId, effect` | **PASS** |
| **CORE-08**<br>`01_Functional` | `GET` | `/decisions/{decisionId}` | Lịch sử quyết định đã xử lý | `200; decisionId` | **PASS** |
| **CORE-09**<br>`01_Functional` | `POST` | `/events` | Gửi sự kiện nghiệp vụ (Polymorphic) | `201; eventId, acceptedAt` | **PASS** |
| **CORE-10**<br>`02_Auth` | `GET` | `/alerts` | Token hợp lệ | `200` | **PASS** |
| **CORE-11**<br>`02_Auth` | `POST` | `/alerts` | Thiếu token | `401/403 (Xử lý có kiểm soát trên Mock)` | **PASS** |
| **CORE-12**<br>`02_Auth` | `POST` | `/alerts` | Token không hợp lệ | `401/403 (Xử lý có kiểm soát trên Mock)` | **PASS** |
| **CORE-13**<br>`03_Negative` | `POST` | `/alerts` | Thiếu field bắt buộc | `400/422; Problem Details (RFC 9457)` | **PASS** |
| **CORE-14**<br>`03_Negative` | `POST` | `/access/check` | `cardId` sai pattern (`RFID-YYYY-NNN`) | `400/422; Problem Details (RFC 9457)` | **PASS** |
| **CORE-15**<br>`03_Negative` | `GET` | `/alerts/{alertId}` | UUID alert không tồn tại | `404; Problem Details (RFC 9457)` | **PASS** |
| **CORE-16**<br>`04_Boundary` | `GET` | `/alerts` | Giới hạn tối thiểu (`limit=1`) | `200` | **PASS** |
| **CORE-17**<br>`04_Boundary` | `GET` | `/alerts` | Giới hạn tối đa (`limit=100`) | `200` | **PASS** |
| **CORE-18**<br>`04_Boundary` | `GET` | `/alerts` | Limit vượt quá giới hạn (`limit=101`) | `400/422` | **PASS** |
| **CORE-19**<br>`05_ConsumerSmoke` | `POST` | `/vision/face-match` | AI Vision mock OK (Bắt tay Consumer) | `2xx; match_status, confidence` | **PASS** |
| **CORE-20**<br>`06_LocalOnly` | `POST` | `/access/check` | Latency SLA ≤ 200ms | `responseTime < 200ms` | **PASS** |

---

## 📝 Chi Tiết Đánh Giá Môi Trường & Quy Trình Kiểm Thử

### 1. Phân loại kịch bản (Categorization)
- **Functional**: Bảo đảm toàn bộ API contract tuân thủ đúng định dạng JSON Schema, trả về đúng các thuộc tính bắt buộc (`id`, `status`, `decisionId`, `acceptedAt`).
- **Auth Verification**: Xử lý linh hoạt phân biệt giữa môi trường Prism Mock (skip kiểm soát do mock không chạy logic JWT auth) và môi trường Local backend (bắt lỗi 401/403).
- **Negative Testing**: Bảo đảm mọi response lỗi tuân thủ định dạng chuẩn **Problem Details (RFC 9457)** bao gồm: `type`, `title`, `status`, `detail`, `instance`.
- **Boundary / Reliability**: Kiểm tra giới hạn tham số phân trang (`limit=1`, `limit=100`, `limit=101`).
- **Consumer-side Smoke Testing**: Kiểm tra tích hợp chéo giữa Core Business và Mock Service của nhóm AI Vision (`http://localhost:4011`).

### 2. Minh chứng Newman Execution
- Report XML đã được tự động sinh tại: `reports/newman-report-core-mock.xml`
- Lệnh chạy kiểm thử tự động:
  ```bash
  npm run test:core:mock
  ```
