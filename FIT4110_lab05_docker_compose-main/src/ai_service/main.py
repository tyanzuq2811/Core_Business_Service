"""
Mock AI Vision Service cho Lab 05 Docker Compose.

Giả lập service AI Vision (nhận diện khuôn mặt) của nhóm AI Vision.
Core Business gọi service này qua mạng nội bộ Docker để kiểm tra kết nối liên service.

Endpoints:
  GET  /health            → trạng thái service
  POST /vision/face-match → giả lập kết quả nhận diện khuôn mặt
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import Body, FastAPI, HTTPException

SERVICE_NAME = os.getenv("SERVICE_NAME", "ai-vision-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock AI Vision Service", version=SERVICE_VERSION)

DETECTIONS_STORE: List[Dict[str, Any]] = [
    {
        "detection_id": "0196fb3d-4ad7-7d1e-9f49-5d5148d2a101",
        "camera_id": "cam-gate-01",
        "detections": [{"label": "person", "confidence": 0.94, "bbox": [100, 60, 220, 380]}],
        "risk_level": "LOW",
        "model_version": "yolov8n-smartcampus-v1.2",
        "timestamp": "2026-05-10T08:00:00Z",
    }
]


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/vision/face-match")
def face_match(payload: Optional[Dict[str, Any]] = Body(default=None)):
    threshold = (payload or {}).get("threshold", 0.75)
    return {
        "match_status": "MATCHED",
        "confidence": max(0.92, float(threshold)),
        "person_id": "STU-2026-001",
        "trace_id": (payload or {}).get("trace_id", f"trace-{uuid.uuid4()}"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/vision/models/info")
def models_info():
    return {
        "service": SERVICE_NAME,
        "models": [
            {"name": "yolov8n-smartcampus", "version": "1.2.0", "task": "object_detection", "status": "LOADED"},
            {"name": "arcface-r50", "version": "1.0.4", "task": "face_recognition", "status": "LOADED"},
        ],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/vision/detect")
def detect_objects(payload: Optional[Dict[str, Any]] = Body(default=None)):
    body = payload or {}
    det_id = str(uuid.uuid4())
    record = {
        "detection_id": det_id,
        "camera_id": body.get("camera_id", "cam-gate-01"),
        "image_url": body.get("image_url", "http://storage.campus.local/images/frame-latest.jpg"),
        "detections": [
            {"label": "person", "confidence": 0.95, "bbox": [110, 45, 240, 410]},
            {"label": "backpack", "confidence": 0.84, "bbox": [135, 190, 210, 310]},
        ],
        "risk_level": "LOW",
        "model_version": "yolov8n-smartcampus-v1.2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    DETECTIONS_STORE.insert(0, record)
    del DETECTIONS_STORE[100:]
    return record


@app.get("/vision/detections/{detection_id}")
def get_detection(detection_id: str):
    for item in DETECTIONS_STORE:
        if item["detection_id"] == detection_id:
            return item
    raise HTTPException(status_code=404, detail=f"Detection '{detection_id}' not found")


@app.get("/vision/results/recent")
def recent_results(limit: int = 10, camera_id: Optional[str] = None):
    items = DETECTIONS_STORE
    if camera_id:
        items = [x for x in items if x.get("camera_id") == camera_id]
    return {"items": items[:limit], "total": len(items)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)