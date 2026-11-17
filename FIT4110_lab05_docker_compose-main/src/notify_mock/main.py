"""
Mock Notification Service cho Lab 05 Docker Compose.

Giả lập Notification Service (gửi thông báo Email/SMS/App Push) của nhóm Notification.
Khi Core Business sinh cảnh báo mức độ cao (HIGH / CRITICAL), Core sẽ gọi Service này để phát tin nhắn khẩn cấp.

Endpoints:
  GET  /health              → trạng thái service
  POST /notifications/send  → nhận yêu cầu phát thông báo
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_NAME = os.getenv("SERVICE_NAME", "notification-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock Notification Service", version=SERVICE_VERSION)

NOTIFICATIONS_LOG: List[Dict[str, Any]] = []


class NotificationRequest(BaseModel):
    recipient: str
    channel: str = "EMAIL"  # EMAIL, SMS, WEBHOOK
    subject: str
    message: str
    severity: Optional[str] = "INFO"


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/notifications/send")
def send_notification(req: NotificationRequest):
    record = {
        "notificationId": f"NOTIF-{str(uuid.uuid4())[:8].upper()}",
        "status": "DELIVERED",
        "channel": req.channel,
        "recipient": req.recipient,
        "subject": req.subject,
        "message": req.message,
        "severity": req.severity,
        "sentAt": datetime.now(timezone.utc).isoformat(),
    }
    NOTIFICATIONS_LOG.insert(0, record)
    del NOTIFICATIONS_LOG[200:]
    return record


@app.get("/notifications")
def list_notifications(limit: int = 20):
    return {"items": NOTIFICATIONS_LOG[:limit], "total": len(NOTIFICATIONS_LOG)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
