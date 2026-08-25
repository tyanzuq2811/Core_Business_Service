"""
Mock IoT Ingestion Service cho Lab 05 Docker Compose.

Giả lập service IoT Ingestion (thu thập dữ liệu cảm biến) của nhóm IoT.
Core Business gọi service này để nhận sự kiện từ thiết bị IoT.

Endpoints:
  GET  /health           → trạng thái service
  POST /readings         → giả lập gửi bản ghi cảm biến
  GET  /readings/latest  → giả lập lấy bản ghi mới nhất
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI

SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock IoT Ingestion Service", version=SERVICE_VERSION)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/readings")
def create_reading():
    return {
        "reading_id": "R-20260510-0001",
        "device_id": "ESP32-LAB-A01",
        "metric": "temperature",
        "accepted": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/readings/latest")
def latest_readings():
    return {
        "items": [
            {
                "reading_id": "R-20260510-0001",
                "device_id": "ESP32-LAB-A01",
                "metric": "temperature",
                "value": 31.5,
                "unit": "celsius",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
