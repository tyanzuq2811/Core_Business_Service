"""
Mock Analytics Service cho Lab 05 Docker Compose.

Giả lập Analytics Service (phân tích thống kê & báo cáo) của nhóm Analytics.
Core Business có thể cung cấp endpoint cho Analytics đọc dữ liệu hoặc gửi dữ liệu thống kê sang Analytics.

Endpoints:
  GET  /health           → trạng thái service
  POST /analytics/events → nhận event để phân tích
  GET  /analytics/summary → trả về báo cáo thống kê tổng hợp
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI

SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock Analytics Service", version=SERVICE_VERSION)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/analytics/events")
def collect_event(event_data: dict):
    return {
        "status": "ACCEPTED",
        "processedAt": datetime.now(timezone.utc).isoformat(),
        "receivedMetric": event_data.get("metric", "general"),
    }


@app.get("/analytics/summary")
def get_summary():
    return {
        "period": "2026-Q3",
        "totalAlerts": 142,
        "totalAccessRequests": 3520,
        "anomaliesDetected": 5,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
