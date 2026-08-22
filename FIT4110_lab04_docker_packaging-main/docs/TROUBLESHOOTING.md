# TROUBLESHOOTING.md — Xử Lý Sự Cố (Core Business Service)

Bảng tổng hợp các lỗi thường gặp khi build, khởi chạy và kiểm thử Docker Container cho **Core Business Service** và cách khắc phục:

| Tình huống / Thông báo lỗi | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop hoặc Docker Engine chưa được bật | Khởi động Docker Desktop trên máy và chờ biểu tượng Docker chuyển sang trạng thái xanh (Running). |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Port 8000 đang bị chiếm dụng bởi tiến trình khác hoặc container cũ | 1. Dừng container cũ: `docker stop fit4110-core-lab04`<br>2. Hoặc map sang port khác: `docker run -p 8001:8000 ...` (đồng thời cập nhật `baseUrl` trong environment Postman). |
| `Conflict. The container name "/fit4110-core-lab04" is already in use` | Container cũ cùng tên đang tồn tại | Chạy lệnh gỡ bỏ container cũ: `docker rm -f fit4110-core-lab04` rồi chạy lại. |
| Container dừng ngay sau khi start | Lỗi cấu hình hoặc thiếu phụ thuộc trong runtime | Kiểm tra log chi tiết: `docker logs fit4110-core-lab04`. |
| `GET /health` trả về kết nối bị từ chối (`ECONNREFUSED`) | Container chưa sẵn sàng hoặc ứng dụng Uvicorn gặp sự cố khi khởi động | Dùng lệnh `docker ps` kiểm tra xem container có đang ở trạng thái `Up` không. Kiểm tra log với `docker logs fit4110-core-lab04`. |
| Lỗi Newman Auth Test `expected 200 to be 401` | Sai lệch `AUTH_TOKEN` giữa `.env.example` và Postman environment | Kiểm tra file `.env.example` và file `postman/environments/FIT4110_lab04_core_local.postman_environment.json` đảm bảo token khớp nhau. |
| Image build quá nặng (> 500MB) | Chưa loại trừ các thư mục phụ thuộc cục bộ khỏi build context | Đảm bảo file `.dockerignore` đã bao gồm `node_modules`, `.venv`, `.git`, `reports`. |
| Lỗi Spectral Linter `No ruleset has been found` | Thiếu file cấu hình quy chuẩn Spectral | Đảm bảo file `.spectral.yaml` tồn tại trong thư mục gốc của project với cấu hình `extends: [spectral:oas]`. |
