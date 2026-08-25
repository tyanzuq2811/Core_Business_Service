"""
Mock Access Gate Service cho Lab 05 Docker Compose.

Giả lập service Access Gate (cổng ra vào) của nhóm Access Gate.
Core Business gọi service này để đồng bộ trạng thái cổng.

Endpoints:
  GET  /health        → trạng thái service
  POST /gates/open    → giả lập mở cổng
  GET  /gates/status  → giả lập lấy trạng thái cổng
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI

SERVICE_NAME = os.getenv("SERVICE_NAME", "access-gate-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock Access Gate Service", version=SERVICE_VERSION)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/gates/open")
def open_gate():
    return {
        "gateId": "GATE-01",
        "action": "OPEN",
        "result": "SUCCESS",
        "openedAt": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/gates/status")
def gate_status():
    return {
        "gates": [
            {"gateId": "GATE-01", "status": "CLOSED", "lastEvent": "2026-05-10T08:00:00Z"},
            {"gateId": "GATE-02", "status": "OPEN", "lastEvent": "2026-05-10T08:15:00Z"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
