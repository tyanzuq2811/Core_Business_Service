# FIT4110 Lab 03 — Báo Cáo Kiểm Thử Hợp Đồng API & Nâng Cao Kiểm Thử Ngoại Lệ

**Thông tin tổng quan:**
- **Service Phụ Trách**: Core Business Service
- **Hệ Thống**: Smart Campus Operations Platform
- **Công Cụ Sử Dụng**: Postman Desktop, Prism Mock Server, Newman CLI (JUnit & HTML Extra Reports)
- **Hợp Đồng OpenAPI**: `contracts/core-business.openapi.yaml` (OpenAPI 3.1.0)
- **Thời Gian Thực Thi Báo Cáo**: 2026-08-16
- **Kết Quả Tổng Quan**: **24/24 Test Cases PASS | 39/39 Assertions PASS (100%)**

---

## 🌐 1. Kiến Trúc Mạng & Các Service Liên Thông Đang Hoạt Động (Realtime Mocks)

Hệ thống đã triển khai đầy đủ **6 Mock Service** phục vụ kiểm thử tích hợp giao tiếp đồng bộ và bất đồng bộ:

| Service Name | Port | Base URL | OpenAPI Specification | Vai trò giao tiếp với Core Business |
| :--- | :---: | :--- | :--- | :--- |
| **Core Business Service** | `4010` | `http://localhost:4010` | `contracts/core-business.openapi.yaml` | Service trung tâm nhận sự kiện, áp dụng rule/policy và tạo alert |
| **AI Vision Service** | `4011` | `http://localhost:4011` | `contracts/ai-vision.openapi.yaml` | Provider so khớp khuôn mặt (`/vision/face-match`) & nhận diện đối tượng |
| **IoT Ingestion Service** | `4012` | `http://localhost:4012` | `contracts/iot-ingestion.openapi.yaml` | Provider thu thập telemetry cảm biến (`/readings`) gửi về cho Core |
| **Access Gate Service** | `4013` | `http://localhost:4013` | `contracts/access-gate.openapi.yaml` | Consumer xin kiểm tra policy ra/vào (`/access/check`) & nhận lệnh mở cổng khẩn cấp |
| **Notification Service** | `4014` | `http://localhost:4014` | `contracts/notification-service.openapi.yaml` | Consumer nhận lệnh đẩy tin nhắn khẩn cấp qua Email/SMS/Push |
| **Analytics Service** | `4015` | `http://localhost:4015` | `contracts/analytics-service.openapi.yaml` | Consumer nhận feed sự kiện để tính toán các chỉ số KPI an ninh campus |

---

## 📊 2. Ma Trận Kiểm Thử Chi Tiết Mới Nhất (24 Test Cases Execution Matrix)

| Test ID | Thư Mục / Folder | HTTP Method | Endpoint | Kịch Bản Kiểm Thử (Scenario) | Status Code | Ref. Run |
| :---: | :--- | :---: | :--- | :--- | :---: | :---: |
| **CORE-01** | `00_Health` | `GET` | `/health` | Kiểm tra service sống (Service Alive Check) | `200 OK` | **PASS** |
| **CORE-02** | `01_Functional` | `POST` | `/alerts` | Tạo cảnh báo mới (Happy Path) | `201 Created` | **PASS** |
| **CORE-03** | `01_Functional` | `GET` | `/alerts` | Lấy danh sách cảnh báo phân trang | `200 OK` | **PASS** |
| **CORE-04** | `01_Functional` | `GET` | `/alerts/recent` | Lấy danh sách cảnh báo gần đây | `200 OK` | **PASS** |
| **CORE-05** | `01_Functional` | `GET` | `/alerts/{alertId}` | Lấy chi tiết 1 cảnh báo theo UUID | `200 OK` | **PASS** |
| **CORE-06** | `01_Functional` | `POST` | `/access/check` | Kiểm tra policy ra/vào realtime | `200 OK` | **PASS** |
| **CORE-07** | `01_Functional` | `GET` | `/policies/access/{policyId}` | Lấy chi tiết Access Policy | `200 OK` | **PASS** |
| **CORE-08** | `01_Functional` | `GET` | `/decisions/{decisionId}` | Tra cứu lịch sử quyết định đã xử lý | `200 OK` | **PASS** |
| **CORE-09** | `01_Functional` | `POST` | `/events` | Gửi sự kiện nghiệp vụ (Polymorphism) | `201 Created` | **PASS** |
| **CORE-10** | `02_Auth` | `GET` | `/alerts` | Yêu cầu kèm Bearer Token hợp lệ | `200 OK` | **PASS** |
| **CORE-11** | `02_Auth` | `POST` | `/alerts` | Yêu cầu thiếu Token (Xử lý linh hoạt Mock/Local) | `401 Unauthorized` | **PASS** |
| **CORE-12** | `02_Auth` | `POST` | `/alerts` | Yêu cầu dùng Token sai (Xử lý linh hoạt Mock/Local) | `401 Unauthorized` | **PASS** |
| **CORE-13** | `03_Negative` | `POST` | `/alerts` | Gửi thiếu field bắt buộc (JSON Schema error) | `422 Unprocessable` | **PASS** |
| **CORE-14** | `03_Negative` | `POST` | `/access/check` | `cardId` sai pattern Regex (`RFID-YYYY-NNN`) | `422 Unprocessable` | **PASS** |
| **CORE-15** | `03_Negative` | `GET` | `/alerts/{alertId}` | Truy vấn UUID cảnh báo không tồn tại | `404 Not Found` | **PASS** |
| **CORE-16** | `03_Negative` | `POST` | `/access/check` | Trùng lặp `idempotencyKey` | `409 Conflict` | **PASS** |
| **CORE-17** | `03_Negative` | `GET` | `/policies/access/{policyId}` | Mã Policy không có trong hệ thống | `404 / 422` | **PASS** |
| **CORE-18** | `03_Negative` | `POST` | `/access/check` | `direction` không đúng Enum (VD: `"SIDEWAYS"`) | `422 Unprocessable` | **PASS** |
| **CORE-19** | `03_Negative` | `POST` | `/alerts` | Giả lập lỗi sự cố Server | `500 Server Error` | **PASS** |
| **CORE-20** | `04_Boundary` | `GET` | `/alerts` | Phân trang cận dưới (`limit=1`) | `200 OK` | **PASS** |
| **CORE-21** | `04_Boundary` | `GET` | `/alerts` | Phân trang cận trên (`limit=100`) | `200 OK` | **PASS** |
| **CORE-22** | `04_Boundary` | `GET` | `/alerts` | Phân trang vượt giới hạn (`limit=101`) | `422 Unprocessable` | **PASS** |
| **CORE-23** | `05_ConsumerSmoke` | `POST` | `/vision/face-match` | Core gọi AI Vision mock (`http://localhost:4011`) | `200 OK` | **PASS** |
| **CORE-24** | `06_LocalOnly` | `POST` | `/access/check` | Kiểm tra SLA thời gian phản hồi ≤ 200ms | `200 OK` | **PASS** |

---

## 📝 3. Chi Tiết Các Kịch Bản Kiểm Thử Ngoại Lệ Bổ Sung (Advanced Negative Tests)

1. **Xung đột trùng lặp Yêu cầu (409 Conflict - Idempotency Key Collision)**:
   - **Kịch bản**: Access Gate bấm quẹt thẻ 2 lần liên tiếp với cùng một `idempotencyKey`.
   - **Kết quả**: Server ngăn chặn giao dịch trùng lặp và phản hồi đúng mã `409 Conflict` kèm mô tả Problem Details (RFC 9457).

2. **Giá trị Enum không hợp lệ (422 Unprocessable Entity - Invalid Enum)**:
   - **Kịch bản**: Client gửi trường `direction` là `"SIDEWAYS"` thay vì `"IN"` hoặc `"OUT"`.
   - **Kết quả**: Validator phát hiện lỗi vi phạm kiểu dữ liệu enum và trả lỗi 422 chi tiết từng thuộc tính bị sai.

3. **Tra cứu Policy không tồn tại (404 Not Found / 422 Client Error)**:
   - **Kịch bản**: Yêu cầu lấy thông tin `POL-NONEXISTENT`.
   - **Kết quả**: Hệ thống phản hồi đúng mã lỗi khách hàng, không gây rò rỉ dữ liệu hoặc lỗi ứng dụng (Crash).

4. **Khả năng khắc phục sự cố hệ thống (500 Internal Server Error Simulation)**:
   - **Kịch bản**: Giả lập sự cố gián đoạn cơ sở dữ liệu backend.
   - **Kết quả**: Hệ thống trả về mã `500 Internal Server Error` chuẩn hoá định dạng Problem Details để phía Client có thể ghi nhận Log lỗi chính xác.

---

## 🚀 4. Lệnh Tự Động Hóa Newman CLI

```bash
# Thực thi bộ kiểm thử mở rộng 24 kịch bản
npm run test:core:mock
```

Tệp báo cáo tự động:
- **XML Report**: `reports/newman-report-core-mock.xml`
- **HTML Report**: `reports/newman-report-core.html`
