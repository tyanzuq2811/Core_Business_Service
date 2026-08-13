# Consumer–Provider Handshake — Core Business Service

## Thông tin chung

- Lab: FIT4110 Lab 03
- Ngày: 2026-08-13
- Provider team: AI Vision Team / Access Gate Team
- Consumer team: Core Business Team (Nhóm Core)
- Provider service: AI Vision Service / Access Gate Service
- Consumer service: Core Business Service

## Contract

- Contract file: `contracts/core-business.openapi.yaml` & `contracts/ai-vision.openapi.yaml`
- Mock base URL: `http://localhost:4010` (Core), `http://localhost:4011` (AI Vision), `http://localhost:4012` (Access Gate)
- Auth method: `Bearer <JWT_TOKEN>`
- Endpoint được test:
  - `POST /access/check` (Access Gate -> Core Business)
  - `POST /vision/face-match` (Core Business -> AI Vision)

## Smoke test

### Request (Core calls AI Vision)

```http
POST /vision/face-match
Authorization: Bearer mock-core-token-2026
Content-Type: application/json
```

```json
{
  "image_url": "https://campus.local/frames/cam01-frame.jpg",
  "threshold": 0.85
}
```

### Expected response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "match_status": "MATCHED",
  "person_id": "STUDENT-2026-089",
  "confidence": 0.96
}
```

## Kết quả

- [x] Consumer gọi mock thành công.
- [x] Consumer parse được field cần dùng (`match_status`, `confidence`, `person_id`).
- [x] Consumer hiểu lỗi 4xx/5xx provider trả về theo chuẩn Problem Details RFC 9457.
- [x] Có Newman report (`reports/newman-report-core-mock.xml`).

## Ghi chú thay đổi hợp đồng

| Nội dung | Trước | Sau | Người đồng ý |
|---|---|---|---|
| Phân biệt casing | snake_case | snake_case cho AI Vision, camelCase cho Core | Core & AI Vision Team |
| Định dạng Lỗi | Custom JSON | Problem Details (RFC 9457) | Core & All Teams |

## Xác nhận

- Provider representative: AI Vision Lead / Access Gate Lead
- Consumer representative: Core Business Lead
