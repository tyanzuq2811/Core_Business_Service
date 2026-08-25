"""
Mock AI Vision Service cho Lab 05 Docker Compose.

Giả lập service AI Vision (nhận diện khuôn mặt) của nhóm AI Vision.
Core Business gọi service này qua mạng nội bộ Docker để kiểm tra kết nối liên service.

Endpoints:
  GET  /health            → trạng thái service
  POST /vision/face-match → giả lập kết quả nhận diện khuôn mặt
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI

SERVICE_NAME = os.getenv("SERVICE_NAME", "ai-vision-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock AI Vision Service", version=SERVICE_VERSION)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/vision/face-match")
def face_match():
    return {
        "match_status": "MATCHED",
        "confidence": 0.96,
        "person_id": "STU-2026-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)