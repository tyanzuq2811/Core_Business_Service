# Engineering Reflection — Core Business Service (`team-core`)

## 1. Những quyết định thiết kế quan trọng

### 1.1. Áp dụng Dual Storage (`PostgreSQL` & `In-Memory`)
- **Bối cảnh**: Trong quá trình phát triển qua các buổi Lab, mã nguồn ban đầu dùng biến toàn cục RAM (Lab 04) khiến dữ liệu mất khi restart container, trong khi ở Lab 05 lại cần PostgreSQL (`smartcampus-core-db`) cho bền vững dữ liệu nhưng đôi lúc cần chạy nhanh không DB để unit test hoặc demo trên máy yếu.
- **Giải pháp**: Tách toàn bộ truy xuất dữ liệu ra lớp trừu tượng `BaseStore` (`src/core_app/storage.py`) với 2 triển khai `PostgresStore` và `InMemoryStore`. Người vận hành chỉ cần đổi `STORAGE_BACKEND=postgres|memory` trong `.env` hoặc bỏ comment trực tiếp 1 dòng trong `create_store()`.
- **Bài học**: Tách tầng lưu trữ giúp controller HTTP (`main.py`) sạch hơn, tránh lặp code SQL rải rác và đảm bảo hành vi nghiệp vụ (như chống trùng lặp `idempotencyKey`) hoạt động nhất quán trên cả hai chế độ.

### 1.2. Tách Side-Effect khỏi Critical Path để giữ SLA `< 200ms`
- **Vấn đề gặp phải**: Ban đầu, `publish_mqtt_event` chạy đồng bộ ngay trong request `POST /alerts`, `POST /access/check` và `POST /vision/detection-result`. Khi MQTT Broker tại địa chỉ LAN không bật (ví dụ chạy local độc lập), `paho-mqtt` chờ TCP timeout tới 2–3 giây, làm vỡ SLA `< 200ms`. Tương tự, `GET /integrations/status` ping tuần tự 5 đối tác khiến một lần quét khi offline mất ~10 giây.
- **Giải pháp**: Đưa MQTT publish và Notification HTTP dispatch vào `FastAPI BackgroundTasks`; chuyển `GET /integrations/status` sang `asyncio.gather` chạy song song trên thread pool với timeout ngắn 1.5s.
- **Kết quả**: Độ trễ API nghiệp vụ luôn duy trì ở mức vài mili-giây ngay cả khi các dịch vụ hạ nguồn tạm ngắt kết nối.

### 1.3. Contract-First với Spectral & Newman trung thực
- **Vấn đề gặp phải**: Khi rà soát báo cáo Lab 05 cũ phát hiện một số kiểm thử Newman trước đây cấu hình URL `/health` cho Consumer Smoke Test, dùng header `Prefer: code=409` thay vì trùng `idempotencyKey` thật, hoặc cho phép `'OFFLINE'`/'error' mà vẫn pass.
- **Giải pháp**: Khôi phục kiểm thử thật: tạo `docker-compose.mock.yml` đấu nối `api` vào 5 mock service nội bộ, nâng cấp mock service đủ endpoint, dùng UUID động (`{{$guid}}`) để kiểm chứng 409 thật sự và bắt buộc khẳng định `status === 'success'` / `onlinePartners === 5` trong môi trường local mock.

---

## 2. Hạn chế còn tồn tại & Hướng phát triển tiếp
1. **Auth giữa các dịch vụ**: Hiện sử dụng Bearer Token tĩnh đối xứng qua biến môi trường (`AUTH_TOKEN`, `GATE_AUTH_TOKEN`, `AI_VISION_AUTH_TOKEN`). Trong môi trường sản xuất có thể nâng cấp lên JWT RS256 ký bởi Identity Provider / API Gateway.
2. **Migration CSDL**: Hiện `PostgresStore` khởi tạo schema bằng `CREATE TABLE IF NOT EXISTS`. Khi mở rộng thêm nhiều bảng phức tạp nên bổ sung công cụ migration như Alembic.
3. **Retry / Dead-letter cho MQTT & Notification**: Hiện `BackgroundTasks` bắn một lần (best-effort). Với hệ thống quy mô lớn nên tích hợp message queue / outbox pattern để đảm bảo gửi lại khi partner tạm thời gián đoạn.
