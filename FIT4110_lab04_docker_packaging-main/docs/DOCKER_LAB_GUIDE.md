# DOCKER_LAB_GUIDE.md — Hướng Dẫn Đóng Gói Docker (Core Business Service)

Tài liệu này giải thích các nguyên lý công nghệ nền tảng và phương pháp đóng gói Docker áp dụng trực tiếp cho **Core Business Service** trong **FIT4110 Lab 04**.

---

## 1. Vì sao cần đóng gói Core Business Service bằng Docker?

Trong các hệ thống phân tán như **Smart Campus Operations Platform**, mỗi thành viên phát triển một service độc lập. Vấn đề kinh điển thường gặp:

```text
"Code chạy tốt trên máy của em nhưng chuyển sang máy bạn hoặc server CI thì bị lỗi môi trường."
```

Docker giải quyết triệt để vấn đề này bằng cách đóng gói toàn bộ:
```text
Mã nguồn (src/core_app/) + Thư viện phụ thuộc (requirements.txt) + Môi trường thực thi (Python 3.11) + Cấu hình runtime (.env.example)
```
thành một Image bất biến (`fit4110/core-business:lab04`) có thể chạy nhất quán trên mọi máy tính và hạ tầng đám mây.

---

## 2. Thiết kế Multi-Stage Build

`Dockerfile` của Core Business Service áp dụng kỹ thuật **Multi-Stage Build** chia làm 2 giai đoạn:

```Dockerfile
# Stage 1: BUILDER — Cài đặt dependencies vào virtual environment
FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip     && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: RUNTIME — Image tinh gọn chỉ chứa venv và mã nguồn
FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup --home /app appuser
COPY --from=builder /opt/venv /opt/venv
COPY src/core_app/ ./src/core_app/
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1
CMD ["sh", "-c", "uvicorn core_app.main:app --app-dir src --host ${APP_HOST} --port ${APP_PORT}"]
```

### Lợi ích của Multi-Stage Build:
1. **Dung lượng nhỏ gọn**: Loại bỏ các công cụ build tạm thời, bánh xe pip cache không cần thiết trong runtime image.
2. **Bảo mật tối đa**: Không để lại build tools hay source mã rác bên trong image triển khai.

---

## 3. Nguyên tắc Bảo mật Non-Root User

Mặc định container chạy bằng user `root`. Nếu ứng dụng bị lỗ hổng RCE (Remote Code Execution), kẻ tấn công có thể chiếm quyền root của máy chủ host.

Trong Dockerfile của Core Business Service:
- Khởi tạo system group `appgroup` và user `appuser`.
- Cấp quyền thư mục `/app` cho `appuser:appgroup`.
- Kích hoạt chỉ thị `USER appuser`. Ứng dụng Uvicorn/FastAPI hoàn toàn chạy với quyền hạn tối thiểu (Principle of Least Privilege).

---

## 4. Docker Native Healthcheck

Container "đang chạy" (status `Up`) không đồng nghĩa với việc "service bên trong đã sẵn sàng phục vụ".

Chỉ thị `HEALTHCHECK` giúp Docker Engine tự động giám sát sức khỏe của Core Business Service:
```Dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3   CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1
```

- **Tần suất**: Thăm dò mỗi 30 giây (`--interval=30s`).
- **Khởi động**: Cho phép ứng dụng 10 giây khởi động ban đầu trước khi tính lỗi (`--start-period=10s`).
- **Thực thi**: Dùng module chuẩn `urllib.request` của Python mà không cần cài thêm công cụ `curl` vào image.

---

## 5. Quản lý Cấu hình & Cách ly Bí mật (Zero-Hardcode)

- Tuyệt đối không commit token bí mật hoặc giá trị cấu hình cố định vào mã nguồn hay Dockerfile.
- Toàn bộ tham số cấu hình được nạp động:
  ```bash
  docker run --env-file .env.example -p 8000:8000 fit4110/core-business:lab04
  ```
- File `.env.example` cung cấp bộ giá trị mặc định chuẩn mực, đảm bảo bất kỳ thành viên nào clone repo về đều có thể chạy thành công ngay lập tức.
