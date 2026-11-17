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
from typing import Dict
from fastapi import FastAPI, HTTPException

SERVICE_NAME = os.getenv("SERVICE_NAME", "access-gate-mock")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

app = FastAPI(title="Mock Access Gate Service", version=SERVICE_VERSION)

CARDS_DB: Dict[str, dict] = {
    "RFID-2026-001": {
        "cardId": "RFID-2026-001",
        "uid": "04:A1:B2:C3:D4:01",
        "ownerName": "Lê Tuấn Dũng",
        "studentId": "1771020189",
        "role": "STUDENT",
        "status": "ACTIVE",
        "allowedGates": ["GATE-01", "GATE-02"],
    },
    "04:A1:B2:C3:D4:01": {
        "cardId": "RFID-2026-001",
        "uid": "04:A1:B2:C3:D4:01",
        "ownerName": "Lê Tuấn Dũng",
        "studentId": "1771020189",
        "role": "STUDENT",
        "status": "ACTIVE",
        "allowedGates": ["GATE-01", "GATE-02"],
    },
    "RFID-2026-999": {
        "cardId": "RFID-2026-999",
        "uid": "04:FF:FF:FF:FF:99",
        "ownerName": "Blacklisted Test Card",
        "role": "GUEST",
        "status": "BLACKLISTED",
        "allowedGates": [],
    },
}

GATES_STATE = {
    "GATE-01": {"gateId": "GATE-01", "status": "CLOSED", "barrier": "READY", "lastEvent": "2026-05-10T08:00:00Z"},
    "GATE-02": {"gateId": "GATE-02", "status": "OPEN", "barrier": "READY", "lastEvent": "2026-05-10T08:15:00Z"},
}

RECENT_LOGS = [
    {
        "logId": "LOG-1001",
        "cardId": "RFID-2026-001",
        "uid": "04:A1:B2:C3:D4:01",
        "gateId": "GATE-01",
        "direction": "IN",
        "granted": True,
        "timestamp": "2026-05-10T08:00:00Z",
    },
    {
        "logId": "LOG-1002",
        "cardId": "RFID-2026-999",
        "uid": "04:FF:FF:FF:FF:99",
        "gateId": "GATE-01",
        "direction": "IN",
        "granted": False,
        "timestamp": "2026-05-10T08:05:00Z",
    },
]


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/gates/open")
def open_gate(gate_id: str = "GATE-01"):
    now = datetime.now(timezone.utc).isoformat()
    GATES_STATE.setdefault(gate_id, {"gateId": gate_id, "barrier": "READY"})
    GATES_STATE[gate_id]["status"] = "OPEN"
    GATES_STATE[gate_id]["lastEvent"] = now
    return {
        "gateId": gate_id,
        "action": "OPEN",
        "result": "SUCCESS",
        "openedAt": now,
    }


@app.get("/gates/status")
def gate_status():
    return {"gates": list(GATES_STATE.values())}


@app.get("/gates/{gate_id}/status")
def single_gate_status(gate_id: str):
    return GATES_STATE.get(
        gate_id,
        {
            "gateId": gate_id,
            "status": "CLOSED",
            "barrier": "READY",
            "lastEvent": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/cards/{card_id}")
def get_card(card_id: str):
    if card_id in CARDS_DB:
        return CARDS_DB[card_id]
    if card_id.startswith("RFID-"):
        return {
            "cardId": card_id,
            "uid": "04:A1:B2:C3:00:00",
            "ownerName": f"Campus Member ({card_id})",
            "role": "STUDENT",
            "status": "ACTIVE",
            "allowedGates": ["GATE-01", "GATE-02"],
        }
    raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found")


@app.get("/access/logs/recent")
def recent_access_logs(limit: int = 5):
    return {"items": RECENT_LOGS[:limit], "total": len(RECENT_LOGS)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
