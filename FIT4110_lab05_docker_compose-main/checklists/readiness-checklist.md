# Readiness Checklist – Core Business Service Stack (Smart Campus)

Đây là danh sách kiểm tra để đảm bảo stack Docker Compose đã sẵn sàng trước khi vận hành và tham gia Plug-a-thon.

- [x] **Database ready:** container `smartcampus-core-db` (PostgreSQL 15) đã chạy và phản hồi `pg_isready`.
- [x] **API Core Business ready:** container `smartcampus-core-service` trả `200` cho `http://localhost:8001/health` và Newman test pass 38/38.
- [x] **Environment variables:** `.env` và `.env.example` đã thiết lập đúng (`HOST_API_PORT=8001`, `APP_PORT=8000`, `AI_VISION_URL`, `IOT_SERVICE_URL`, `GATE_SERVICE_URL`, `ANALYTICS_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`). Không sử dụng secret thật.
- [x] **Network & Ports:** mạng `smartcampus-network` kết nối các service; port 8001 (API) và 5433 (DB) được map đúng (Host:Container).
- [x] **Non-root user:** Container API chạy bằng `appuser`, không dùng root.
- [x] **Healthcheck & Startup Order:** Service API phụ thuộc vào Database với `condition: service_healthy`.
- [x] **LAN Dashboard ready:** Endpoint `GET /integrations/status` kiểm tra đồng thời toàn bộ đối tác trong mạng LAN.

Ghi chú:
```
- Tên container đã được chuẩn hoá toàn dự án: smartcampus-core-service & smartcampus-core-db.
- Sẵn sàng giao tiếp với các nhóm AI Vision, IoT, Access Gate, Analytics, Notification qua mạng LAN.
```