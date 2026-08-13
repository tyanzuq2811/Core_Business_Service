# Phân tích yêu cầu — vai Consumer

- Cặp đàm phán: #2 (Core → AI Vision) và #3 (Core → Access Gate)
- Product: A / B
- Consumer service: Core Business
- Provider service: AI Vision, Access Gate
- Người viết: Nhóm Core Business
- Ngày: 2026-08-11

---

## Phần A — Core Business gọi AI Vision (cặp #2)

### A1. Resource Consumer cần nhận

> **Lưu ý**: Nhóm AI Vision sử dụng convention **snake_case** cho field name trong API của họ.

| Resource | Consumer dùng để làm gì? | Field bắt buộc | Field tùy chọn |
|---|---|---|---|
| `DetectResponse` | Đánh giá có người lạ/vật thể bất thường không để tạo alert | `detection_id`, `camera_id`, `detections[]`, `risk_level`, `model_version`, `timestamp` | `processing_time_ms` |
| `FaceMatchResponse` | Kiểm tra khuôn mặt khớp với whitelist/blacklist | `match_id`, `matched`, `confidence`, `threshold`, `status`, `trace_id` | `message`, `model_version`, `processing_time_ms` |

### A2. API Consumer cần gọi

| Method | Path | Lúc nào gọi? | Kỳ vọng response |
|---|---|---|---|
| POST | `/vision/face-match` | Khi Camera Stream phát hiện người lạ, Core yêu cầu AI Vision match | `FaceMatchResponse` với `matched` (bool), `confidence` (0.0–1.0), `status` (MATCHED/NOT_MATCHED/LOW_CONFIDENCE) |
| GET | `/vision/detections/{detectionId}` | Khi cần lấy chi tiết một kết quả phát hiện | `DetectResponse` object đầy đủ |
| GET | `/vision/results/recent` | Định kỳ hoặc khi cần tổng hợp kết quả gần đây | `DetectionPage` (mảng `DetectResponse[]` + cursor pagination) |

### A3. Error case Consumer cần xử lý

| Status | Consumer hiểu là gì? | Consumer sẽ xử lý thế nào? |
|---:|---|---|
| 400 | Request sai schema (thiếu field, sai format ảnh) | Log lỗi, không tạo alert |
| 401 | Token hết hạn | Refresh token và retry |
| 404 | `detection_id` không tồn tại | Bỏ qua, log warning |
| 408 | AI Vision xử lý ảnh quá lâu (timeout) | Retry 1 lần với ảnh nhỏ hơn |
| 413 | Ảnh gửi lên quá lớn (>10MB) | Resize ảnh và gửi lại |
| 422 | Ảnh đúng format nhưng không xử lý được (quá mờ) | Log, đánh dấu inconclusive |
| 500 | AI Vision lỗi nội bộ | Retry 1 lần, sau đó log và skip |
| 503 | AI Vision đang load model hoặc bảo trì | Chờ và retry sau 5s |

---

## Phần B — Core Business gọi Access Gate (cặp #3)

### B1. Resource Consumer cần nhận

| Resource | Consumer dùng để làm gì? | Field bắt buộc | Field tùy chọn |
|---|---|---|---|
| `AccessLog` | Kiểm tra/audit lượt ra vào, phát hiện bất thường | `logId`, `cardId`, `gateId`, `direction`, `status`, `timestamp` | `personId`, `operatorNote` |
| `GateStatus` | Biết trạng thái cổng (mở/đóng/lỗi) | `gateId`, `status`, `lastUpdated` | `errorMessage` |

### B2. API Consumer cần gọi

| Method | Path | Lúc nào gọi? | Kỳ vọng response |
|---|---|---|---|
| GET | `/access/logs/recent` | Khi cần kiểm tra lượt ra/vào gần đây | Mảng `AccessLog[]` |
| GET | `/access/logs/{logId}` | Khi cần chi tiết một lượt quẹt thẻ | `AccessLog` object |
| GET | `/gates/{gateId}/status` | Khi cần biết cổng đang mở hay đóng | `GateStatus` object |
| GET | `/cards/{cardId}` | Khi cần tra thông tin thẻ | Thông tin card holder |

### B3. Error case Consumer cần xử lý

| Status | Consumer hiểu là gì? | Consumer sẽ xử lý thế nào? |
|---:|---|---|
| 400 | Query parameter sai | Sửa request và retry |
| 401 | Thiếu token | Cấu hình lại token |
| 403 | Không có quyền xem log | Báo admin cấp quyền |
| 404 | `logId` hoặc `gateId` không tồn tại | Hiển thị không tìm thấy |
| 500 | Access Gate lỗi | Retry 1 lần, log lỗi |

---

## 4. Giả định bổ sung

- Giả định 1: AI Vision trả kết quả trong ≤2s cho face-match.
- Giả định 2: Access Gate lưu log ít nhất 30 ngày.
- Giả định 3: Cả hai Provider đều dùng camelCase cho field name.

---

## 5. Câu hỏi cho Provider

1. (AI Vision) Core gửi `imageRef` (URL) hay `faceEmbedding` (vector) khi gọi face-match?
2. (AI Vision) Ngưỡng confidence bao nhiêu thì coi là match?
3. (Access Gate) Log lưu bao lâu? Core có được query theo khoảng thời gian không?
4. (Access Gate) Card bị khóa thì trả status code nào?

---

## 6. Rủi ro tích hợp

| Rủi ro | Tác động | Đề xuất xử lý |
|---|---|---|
| AI Vision trả confidence khác thang điểm | Core đánh giá sai mức rủi ro | Chốt thang 0.0–1.0 trong openapi.yaml |
| Access Gate đổi format log | Core parse lỗi | Chốt schema rõ ràng, có version |
| Provider thay đổi enum value | Core if/switch lỗi | Liệt kê enum đầy đủ trong contract |
