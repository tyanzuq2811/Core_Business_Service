# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1: BUILDER — Cài đặt dependencies vào virtual env
# ============================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements.txt .

RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ============================================================
# Stage 2: RUNTIME — Image siêu nhẹ, chỉ chứa code + venv
# ============================================================
FROM python:3.11-slim AS runtime

LABEL maintainer="FIT4110 Core Business Team"
LABEL description="Smart Campus — Core Business Service (Lab 04)"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Giá trị mặc định — có thể ghi đè bởi --env-file hoặc -e khi chạy
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

WORKDIR /app

# Tạo user riêng (non-root) để tránh chạy bằng quyền root
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /app appuser

# Copy virtual env đã build từ stage 1
COPY --from=builder /opt/venv /opt/venv

# Chỉ copy đúng module core_app (không copy iot_app hay các thư mục thừa)
COPY src/core_app/ ./src/core_app/

# Phân quyền thư mục cho appuser
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE ${APP_PORT}

# Healthcheck tự động — Docker daemon sẽ gọi định kỳ
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${APP_PORT}/health', timeout=3).read()" || exit 1

CMD ["sh", "-c", "uvicorn core_app.main:app --app-dir src --host ${APP_HOST} --port ${APP_PORT}"]
