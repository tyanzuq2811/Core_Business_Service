# Docker Evidence — Lab 04: Core Business Service

## Thông Tin Nhóm
- **Nhóm:** Team Core Business (`team-core`)
- **Service:** Core Business Service
- **Image Tag Quy Ước:** `fit4110/core-business:lab04` | `v0.1.0-core-business`

---

## 1. Bằng chứng Build Docker Image
**Lệnh thực hiện:**
```bash
docker build -t fit4110/core-business:lab04 .
```

**Kết quả:**
```text
#1 [internal] load build definition from Dockerfile
#2 resolve image config for docker-image://docker.io/docker/dockerfile:1.7
#3 [builder 1/5] FROM docker.io/library/python:3.11-slim
#4 [builder 4/5] COPY requirements.txt .
#5 [builder 5/5] RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
#6 [runtime 4/6] COPY --from=builder /opt/venv /opt/venv
#7 [runtime 5/6] COPY src/core_app/ ./src/core_app/
#8 [runtime 6/6] RUN chown -R appuser:appgroup /app
#9 naming to docker.io/fit4110/core-business:lab04 done
```

---

## 2. Bằng chứng Khởi chạy Docker Container
**Lệnh thực hiện:**
```bash
docker run -d --rm --name fit4110-core-lab04 -p 8000:8000 --env-file .env.example fit4110/core-business:lab04
```

**Trạng thái Container:**
```text
CONTAINER ID   IMAGE                          COMMAND                  STATUS                   PORTS
870ffb9c9dc0   fit4110/core-business:lab04   "sh -c 'uvicorn core…"   Up 2 minutes (healthy)   0.0.0.0:8000->8000/tcp
```

---

## 3. Bằng chứng Kiểm tra Healthcheck
**Lệnh thực hiện:**
```bash
curl http://localhost:8000/health
```

**Phản hồi:**
```json
{
  "status": "ok",
  "service": "core-business",
  "version": "0.4.0",
  "time": "2026-08-22T08:00:00Z"
}
```

---

## 4. Bằng chứng Kiểm thử Tự động Newman
**Lệnh thực hiện:**
```bash
npm run test:local
```

**Kết quả tổng hợp:**
```text
┌─────────────────────────┬─────────────────┬─────────────────┐
│                         │        executed │          failed │
├─────────────────────────┼─────────────────┼─────────────────┤
│              iterations │               1 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│                requests │              24 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│            test-scripts │              24 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│      prerequest-scripts │              24 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│              assertions │              38 │               0 │
├─────────────────────────┴─────────────────┴─────────────────┤
│ total run duration: 1484ms                                  │
└─────────────────────────────────────────────────────────────┘
```

**File Báo cáo:**
- `reports/newman-lab04-local.html`
- `reports/newman-lab04-local.xml`
