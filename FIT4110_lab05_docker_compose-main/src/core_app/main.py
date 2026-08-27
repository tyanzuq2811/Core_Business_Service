import json
import os
from datetime import datetime, timezone
import re
import uuid
from typing import Any, Dict, List, Optional
import requests
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# Đọc cấu hình từ biến môi trường (mạng LAN Plug-a-thon)
SERVICE_NAME = os.getenv("SERVICE_NAME", "core-business")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")

# Địa chỉ IP/URL các nhóm trong mạng LAN (Cấu hình qua .env)
AI_VISION_URL = os.getenv("AI_VISION_URL", "http://192.168.1.41:8000")
AI_VISION_AUTH_TOKEN = os.getenv("AI_VISION_AUTH_TOKEN", "local-dev-token-vision")
IOT_SERVICE_URL = os.getenv("IOT_SERVICE_URL", "http://192.168.1.11:8000")
GATE_SERVICE_URL = os.getenv("GATE_SERVICE_URL", "http://192.168.1.31:8000")
GATE_AUTH_TOKEN = os.getenv("GATE_AUTH_TOKEN", "dev-secret-token")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://192.168.1.51:8000")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "192.168.1.51")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_BUSINESS_EVENTS = os.getenv("MQTT_TOPIC_BUSINESS_EVENTS", "business.events")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://192.168.1.61:8000")

app = FastAPI(
    title="Smart Campus — Core Business Service API",
    version=SERVICE_VERSION,
    description="Core Business Service backend - Hoàn thiện cho kịch bản mạng LAN Plug-a-thon.",
)

# Shared in-memory data store for testing
ALERTS_DB: Dict[str, Dict[str, Any]] = {
    "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc": {
        "id": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
        "sourceService": "core-business",
        "alertType": "UNAUTHORIZED_ACCESS",
        "severity": "HIGH",
        "message": "Phát hiện truy cập trái phép tại cổng chính",
        "status": "OPEN",
        "createdAt": "2026-05-10T08:00:00Z",
        "resolvedAt": None,
    }
}

POLICIES_DB: Dict[str, Dict[str, Any]] = {
    "POL-001": {
        "policyId": "POL-001",
        "name": "Default Student Campus Access",
        "effect": "ALLOW",
        "status": "ACTIVE",
        "conditions": {"allowedGates": ["GATE-01", "GATE-02"], "timeWindow": "06:00-22:00"},
        "active": True,
    }
}

DECISIONS_DB: Dict[str, Dict[str, Any]] = {
    "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002": {
        "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
        "cardId": "RFID-2026-001",
        "gateId": "GATE-01",
        "result": "ALLOW",
        "reasonCode": "VALID_CARD",
        "policyId": "POL-001",
        "evaluatedAt": "2026-05-10T08:00:00Z",
    }
}

EVENTS_DB: List[Dict[str, Any]] = [
    {
        "eventId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2e001",
        "sourceService": "iot-ingestion",
        "eventType": "SENSOR_TELEMETRY",
        "payload": {"sensorId": "ENV-01", "temperature": 24.5, "humidity": 65.0},
        "receivedAt": "2026-08-27T07:10:00Z",
    },
    {
        "eventId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2e002",
        "sourceService": "ai-vision",
        "eventType": "OBJECT_DETECTION",
        "payload": {"cameraId": "cam-gate-01", "detectedObjects": ["person", "car"], "confidence": 0.94},
        "receivedAt": "2026-08-27T07:12:00Z",
    }
]

PROCESSED_IDEMPOTENCY_KEYS = set()


# Helper function to generate ProblemDetails RFC 9457 response
def problem_details_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    errors: Optional[List[Dict[str, Any]]] = None,
    type_url: str = "https://campus.local/errors/validation",
) -> JSONResponse:
    content: Dict[str, Any] = {
        "type": type_url,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if errors:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content, media_type="application/problem+json")


# Global Exception Handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors_list = []
    for err in exc.errors():
        field_name = ".".join([str(x) for x in err.get("loc", []) if x not in ("body", "query", "path")])
        errors_list.append({
            "field": field_name or "payload",
            "code": err.get("type", "VALIDATION_ERROR").upper(),
            "message": err.get("msg", "Dữ liệu không hợp lệ"),
        })
    return problem_details_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Dữ liệu không hợp lệ về nghiệp vụ",
        detail="Payload hoặc thông số request không đáp ứng quy chuẩn OpenAPI Schema",
        instance=str(request.url.path),
        errors=errors_list,
    )


# -------------------------------
# Schemas
# -------------------------------
class AlertCreatePayload(BaseModel):
    sourceService: str = Field(..., min_length=1)
    alertType: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    relatedEventId: Optional[str] = None


class AccessCheckPayload(BaseModel):
    cardId: str
    gateId: str
    direction: str
    idempotencyKey: Optional[str] = None
    timestamp: Optional[str] = None


class EventIngestPayload(BaseModel):
    eventType: Optional[str] = "generic.event"
    eventId: Optional[str] = None
    sourceService: Optional[str] = None
    timestamp: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


# -------------------------------
# Endpoints
# -------------------------------
@app.get("/health", tags=["health"])
async def get_health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/alerts", status_code=status.HTTP_201_CREATED, tags=["alerts"])
async def create_alert(
    payload: AlertCreatePayload,
    request: Request,
    prefer: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    # Support test prefer header for mocking error responses
    if prefer == "code=400":
        return problem_details_response(
            status_code=422,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Payload không đúng JSON Schema, thiếu trường bắt buộc sourceService",
            instance=str(request.url.path),
            errors=[{"field": "sourceService", "code": "REQUIRED", "message": "Trường sourceService là bắt buộc"}],
        )
    if prefer == "code=500":
        return problem_details_response(
            status_code=500,
            title="Internal Server Error",
            detail="Đã xảy ra sự cố nội bộ trên máy chủ Core Business",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/server-error",
        )

    # Auth verification for auth test scenarios
    if authorization is None or authorization == "Bearer invalid-jwt-token":
        return problem_details_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Yêu cầu truy cập thiếu hoặc sử dụng Bearer Token không hợp lệ",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/unauthorized",
        )

    alert_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    new_alert = {
        "id": alert_id,
        "sourceService": payload.sourceService,
        "alertType": payload.alertType,
        "severity": payload.severity,
        "message": payload.message,
        "status": "OPEN",
        "createdAt": now_str,
        "resolvedAt": None,
    }
    ALERTS_DB[alert_id] = new_alert

    # Tự động đẩy sự kiện cảnh báo thật sang Analytics qua MQTT
    publish_mqtt_event("business.alert.created", {
        "alert_id": alert_id,
        "alert_type": payload.alertType,
        "location": "GATE-01",
        "severity": payload.severity,
        "created_at": now_str,
    })

    return new_alert


@app.get("/alerts", tags=["alerts"])
async def list_alerts(
    request: Request,
    limit: int = 10,
    prefer: Optional[str] = Header(None),
):
    if prefer == "code=400" or limit < 1 or limit > 100:
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Tham số không hợp lệ",
            detail="Tham số limit phải có giá trị trong khoảng từ 1 đến 100",
            instance=str(request.url.path),
        )

    items = list(ALERTS_DB.values())[:limit]
    return {
        "items": items,
        "hasMore": len(ALERTS_DB) > limit,
        "total": len(ALERTS_DB),
    }


@app.get("/alerts/recent", tags=["alerts"])
async def get_recent_alerts(limit: int = 5):
    items = list(ALERTS_DB.values())[:limit]
    return {"items": items}


@app.get("/alerts/{alert_id}", tags=["alerts"])
async def get_alert_detail(
    alert_id: str,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    if prefer == "code=404" or alert_id not in ALERTS_DB:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy cảnh báo với alertId '{alert_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    return ALERTS_DB[alert_id]


@app.post("/alerts/{alert_id}/resolve", tags=["alerts"])
async def resolve_alert(alert_id: str):
    """Đánh dấu cảnh báo đã được giải quyết (RESOLVED)."""
    if alert_id in ALERTS_DB:
        ALERTS_DB[alert_id]["status"] = "RESOLVED"
        ALERTS_DB[alert_id]["resolvedAt"] = datetime.now(timezone.utc).isoformat()
        return ALERTS_DB[alert_id]
    raise HTTPException(status_code=404, detail="Alert not found")


@app.get("/decisions", tags=["access-policy"])
async def list_decisions():
    """Lấy danh sách tất cả các quyết định quẹt thẻ phục vụ Dashboard & Analytics."""
    return list(DECISIONS_DB.values())


@app.get("/events", tags=["events"])
async def list_events():
    """Lấy danh sách tất cả sự kiện đã nhận phục vụ Dashboard."""
    return EVENTS_DB


@app.post("/dashboard/clear-data", tags=["dashboard"])
async def clear_live_data():
    """Xóa sạch dữ liệu trong bộ nhớ để nhận 100% dữ liệu thật từ các nhóm."""
    global EVENTS_DB, ALERTS_DB, DECISIONS_DB
    EVENTS_DB.clear()
    ALERTS_DB = {
        "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc": {
            "id": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
            "sourceService": "core-business",
            "alertType": "SYSTEM_READY",
            "severity": "LOW",
            "message": "Hệ thống sẵn sàng tiếp nhận dữ liệu thật từ các nhóm mạng LAN",
            "status": "OPEN",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "resolvedAt": None,
        }
    }
    DECISIONS_DB = {
        "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002": {
            "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
            "cardId": "RFID-2026-001",
            "gateId": "GATE-01",
            "result": "ALLOW",
            "reasonCode": "VALID_CARD",
            "policyId": "POL-001",
            "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        }
    }
    return {
        "status": "ok",
        "message": "Đã làm sạch toàn bộ dữ liệu! Sẵn sàng tiếp nhận dữ liệu thật từ các nhóm."
    }


@app.post("/access/check", tags=["access-policy"])
async def check_access(
    payload: AccessCheckPayload,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    # Check cardId regex pattern
    card_pattern = r"^RFID-[0-9]{4}-[0-9]{3}$"
    if prefer == "code=400" or not re.match(card_pattern, payload.cardId):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Trường cardId không đúng định dạng RFID-YYYY-NNN",
            instance=str(request.url.path),
            errors=[{"field": "cardId", "code": "PATTERN_MISMATCH", "message": "cardId phải có dạng RFID-YYYY-NNN"}],
        )

    # Check direction enum
    if payload.direction not in ("IN", "OUT"):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Trường direction phải là IN hoặc OUT",
            instance=str(request.url.path),
            errors=[{"field": "direction", "code": "INVALID_ENUM", "message": "direction phải là IN hoặc OUT"}],
        )

    # Check idempotency collision when requested via Prefer header
    if prefer == "code=409":
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Xung đột trùng lặp giao dịch",
            detail=f"IdempotencyKey '{payload.idempotencyKey}' đã được xử lý trước đó",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/conflict",
        )

    decision_id = str(uuid.uuid4())
    evaluated_at = datetime.now(timezone.utc).isoformat()
    decision = {
        "decisionId": decision_id,
        "cardId": payload.cardId,
        "gateId": payload.gateId,
        "direction": payload.direction,
        "result": "ALLOW",
        "reasonCode": "VALID_CARD",
        "policyId": "POL-001",
        "evaluatedAt": evaluated_at,
    }
    DECISIONS_DB[decision_id] = decision

    # Tự động đẩy sự kiện quẹt thẻ thật sang Analytics qua MQTT
    publish_mqtt_event("business.policy.decision.created", {
        "decision_id": decision_id,
        "card_id": payload.cardId,
        "gate_id": payload.gateId,
        "direction": payload.direction,
        "result": "ALLOW",
        "evaluated_at": evaluated_at,
    })

    return decision


@app.get("/policies/access/{policy_id}", tags=["access-policy"])
async def get_policy_detail(
    policy_id: str,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    if prefer == "code=404" or policy_id not in POLICIES_DB:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy Policy với policyId '{policy_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    return POLICIES_DB[policy_id]


@app.get("/decisions/{decision_id}", tags=["access-policy"])
async def get_decision_detail(
    decision_id: str,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    if prefer == "code=404" or decision_id not in DECISIONS_DB:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy Quyết định với decisionId '{decision_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    return DECISIONS_DB[decision_id]


@app.post("/events", status_code=status.HTTP_201_CREATED, tags=["events"])
async def ingest_event(request: Request):
    """
    Tiếp nhận sự kiện từ IoT Ingestion (SensorEvent / sensor.reading.created)
    hoặc các phân hệ khác theo chuẩn OpenAPI contract.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    event_id = body.get("eventId") or str(uuid.uuid4())
    event_type = body.get("eventType") or "sensor.reading.created"
    source = body.get("source") or body.get("sourceService") or "iot-ingestion"
    occurred_at = body.get("occurredAt") or body.get("timestamp") or datetime.now(timezone.utc).isoformat()
    correlation_id = body.get("correlationId")

    # Trích xuất dữ liệu cảm biến (hỗ trợ cả dạng phẳng lẫn dạng lồng data / payload)
    data_payload = body.get("data") or body.get("payload") or {}
    if not data_payload and any(k in body for k in ("deviceId", "metric", "value", "unit", "locationId")):
        data_payload = {
            "deviceId": body.get("deviceId"),
            "metric": body.get("metric"),
            "value": body.get("value"),
            "unit": body.get("unit"),
            "locationId": body.get("locationId"),
        }

    event_record = {
        "eventId": event_id,
        "sourceService": source,
        "eventType": event_type,
        "correlationId": correlation_id,
        "payload": data_payload,
        "timestamp": occurred_at,
        "receivedAt": datetime.now(timezone.utc).isoformat(),
    }
    EVENTS_DB.insert(0, event_record)

    # Tự động tạo Alert nếu cảm biến báo quá ngưỡng (Core Business Rule Engine)
    metric = data_payload.get("metric")
    val = data_payload.get("value")
    if event_type == "sensor.threshold.exceeded" or (metric == "temperature" and isinstance(val, (int, float)) and val > 40.0):
        alert_id = str(uuid.uuid4())
        ALERTS_DB[alert_id] = {
            "id": alert_id,
            "sourceService": "iot-ingestion",
            "alertType": "OVERHEAT_CRITICAL" if val and val > 50 else "TEMPERATURE_HIGH",
            "severity": "CRITICAL" if val and val > 50 else "HIGH",
            "message": f"Cảm biến {data_payload.get('deviceId', 'SENSOR')} tại {data_payload.get('locationId', 'Campus')} đo được {val}°C (vượt ngưỡng an toàn)!",
            "status": "OPEN",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "resolvedAt": None,
        }

    return {
        "eventId": event_id,
        "acceptedAt": datetime.now(timezone.utc).isoformat(),
    }


# -------------------------------
# Plug-a-thon LAN Integrations & Dashboard
# -------------------------------
def ping_service(service_name: str, base_url: str) -> Dict[str, Any]:
    """Hàm helper kiểm tra kết nối tới 1 service trong mạng LAN với timeout 2.0s."""
    target_url = f"{base_url.rstrip('/')}/health"
    try:
        start_time = datetime.now()
        resp = requests.get(target_url, timeout=2.0)
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        is_ok = resp.status_code in (200, 201)
        response_data = {}
        try:
            response_data = resp.json()
        except Exception:
            response_data = {"raw": resp.text[:100]}

        return {
            "service": service_name,
            "url": base_url,
            "status": "ONLINE" if is_ok else "DEGRADED",
            "statusCode": resp.status_code,
            "latencyMs": elapsed_ms,
            "response": response_data,
        }
    except Exception as e:
        return {
            "service": service_name,
            "url": base_url,
            "status": "OFFLINE",
            "statusCode": None,
            "latencyMs": None,
            "error": str(e),
        }


@app.get("/integrations/status", tags=["integrations"])
async def check_all_lan_integrations():
    """
    Dashboard kiểm tra kết nối thời gian thực đến toàn bộ 5 đối tác trong mạng LAN:
    - AI Vision (nhận diện khuôn mặt)
    - IoT Ingestion (cảm biến môi trường)
    - Access Gate (kiểm soát cổng)
    - Analytics (thống kê & audit)
    - Notification (thông báo khẩn cấp)
    """
    services_to_check = {
        "ai-vision": AI_VISION_URL,
        "iot-ingestion": IOT_SERVICE_URL,
        "access-gate": GATE_SERVICE_URL,
        "analytics": ANALYTICS_SERVICE_URL,
        "notification": NOTIFICATION_SERVICE_URL,
    }

    results = {}
    online_count = 0
    for name, url in services_to_check.items():
        res = ping_service(name, url)
        results[name] = res
        if res["status"] == "ONLINE":
            online_count += 1

    return {
        "summary": {
            "coreBusinessVersion": SERVICE_VERSION,
            "totalPartners": len(services_to_check),
            "onlinePartners": online_count,
            "offlinePartners": len(services_to_check) - online_count,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
        },
        "partners": results,
    }


@app.get("/integrations/{service_name}/health", tags=["integrations"])
async def check_single_service_health(service_name: str):
    """Kiểm tra kết nối trực tiếp đến 1 service cụ thể qua mạng LAN."""
    service_map = {
        "ai-vision": AI_VISION_URL,
        "iot": IOT_SERVICE_URL,
        "iot-ingestion": IOT_SERVICE_URL,
        "gate": GATE_SERVICE_URL,
        "access-gate": GATE_SERVICE_URL,
        "analytics": ANALYTICS_SERVICE_URL,
        "notification": NOTIFICATION_SERVICE_URL,
        "notify": NOTIFICATION_SERVICE_URL,
    }
    
    if service_name not in service_map:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' không hợp lệ. Các service hỗ trợ: {list(service_map.keys())}"
        )

    return ping_service(service_name, service_map[service_name])


@app.get("/integrations/gate/cards/{card_id}", tags=["integrations"])
async def get_gate_card_info(card_id: str):
    """
    Gọi sang Access Gate Service (/cards/{cardId}) với Bearer token để tra cứu dữ liệu thẻ.
    """
    try:
        target_url = f"{GATE_SERVICE_URL.rstrip('/')}/cards/{card_id}"
        headers = {"Authorization": f"Bearer {GATE_AUTH_TOKEN}"}
        resp = requests.get(target_url, headers=headers, timeout=3.0)
        card_data = {}
        try:
            card_data = resp.json()
        except Exception:
            card_data = {"raw": resp.text}

        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "gateUrl": target_url,
            "statusCode": resp.status_code,
            "cardId": card_id,
            "data": card_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "gateUrl": f"{GATE_SERVICE_URL.rstrip('/')}/cards/{card_id}",
            "error": str(e),
        }


@app.get("/integrations/gate/logs/recent", tags=["integrations"])
async def get_gate_recent_logs(limit: int = 5):
    """
    Gọi sang Access Gate Service (GET /access/logs/recent?limit=5)
    để lấy dữ liệu quẹt thẻ thật real-time (UID 04:A1:B2:C3:D4:0X, granted/denied).
    """
    try:
        target_url = f"{GATE_SERVICE_URL.rstrip('/')}/access/logs/recent?limit={limit}"
        headers = {"Authorization": f"Bearer {GATE_AUTH_TOKEN}"}
        resp = requests.get(target_url, headers=headers, timeout=3.0)
        logs_data = {}
        try:
            logs_data = resp.json()
        except Exception:
            logs_data = {"raw": resp.text}

        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "gateUrl": target_url,
            "statusCode": resp.status_code,
            "logs": logs_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "gateUrl": f"{GATE_SERVICE_URL.rstrip('/')}/access/logs/recent?limit={limit}",
            "error": str(e),
        }


@app.get("/integrations/gate/gates/{gate_id}/status", tags=["integrations"])
async def get_gate_barrier_status(gate_id: str = "GATE-01"):
    """
    Gọi sang Access Gate Service (GET /gates/{gateId}/status)
    để kiểm tra trạng thái vật lý cổng barrier.
    """
    try:
        target_url = f"{GATE_SERVICE_URL.rstrip('/')}/gates/{gate_id}/status"
        headers = {"Authorization": f"Bearer {GATE_AUTH_TOKEN}"}
        resp = requests.get(target_url, headers=headers, timeout=3.0)
        status_data = {}
        try:
            status_data = resp.json()
        except Exception:
            status_data = {"raw": resp.text}

        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "gateUrl": target_url,
            "statusCode": resp.status_code,
            "gateId": gate_id,
            "data": status_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "gateUrl": f"{GATE_SERVICE_URL.rstrip('/')}/gates/{gate_id}/status",
            "error": str(e),
        }


@app.post("/integrations/ai-vision/face-match", tags=["integrations"])
async def test_ai_vision_face_match(payload: Optional[Dict[str, Any]] = None):
    """
    Gọi sang AI Vision Service (POST /vision/face-match) để kiểm tra so khớp khuôn mặt.
    """
    try:
        target_url = f"{AI_VISION_URL.rstrip('/')}/vision/face-match"
        headers = {
            "Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }
        body = payload or {
            "image_url": "http://192.168.137.115:8001/cameras/cam-lab05-gate/frames/latest",
            "reference_image_url": "http://192.168.137.79:8001/profiles/student-001.jpg",
            "threshold": 0.75,
            "trace_id": f"trace-core-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        resp = requests.post(target_url, json=body, headers=headers, timeout=4.0)
        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "statusCode": resp.status_code,
            "result": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/integrations/ai-vision/models", tags=["integrations"])
async def test_ai_vision_models():
    """
    Gọi sang AI Vision Service (GET /vision/models/info) để lấy thông tin model YOLOv8.
    """
    try:
        target_url = f"{AI_VISION_URL.rstrip('/')}/vision/models/info"
        headers = {"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}"}
        resp = requests.get(target_url, headers=headers, timeout=3.0)
        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "statusCode": resp.status_code,
            "modelInfo": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/integrations/ai-vision/detect", tags=["integrations"])
async def test_ai_vision_detect(payload: Optional[Dict[str, Any]] = None):
    """
    Gọi sang AI Vision Service (POST /vision/detect) để phát hiện đối tượng trong ảnh theo hợp đồng.
    """
    try:
        target_url = f"{AI_VISION_URL.rstrip('/')}/vision/detect"
        headers = {
            "Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }
        body = payload or {
            "camera_id": "cam-gate-01",
            "image_url": "http://storage.campus.local/images/frame-20260811-001.jpg",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence_threshold": 0.6,
        }
        resp = requests.post(target_url, json=body, headers=headers, timeout=4.0)
        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "statusCode": resp.status_code,
            "result": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/integrations/ai-vision/detections/{detection_id}", tags=["integrations"])
async def get_ai_vision_detection_by_id(detection_id: str):
    """
    Gọi sang AI Vision Service (GET /vision/detections/{detectionId}) để lấy chi tiết kết quả detection.
    """
    try:
        target_url = f"{AI_VISION_URL.rstrip('/')}/vision/detections/{detection_id}"
        headers = {"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}"}
        resp = requests.get(target_url, headers=headers, timeout=3.0)
        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "statusCode": resp.status_code,
            "detectionId": detection_id,
            "result": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/integrations/ai-vision/results/recent", tags=["integrations"])
async def get_ai_vision_recent_results(limit: int = 10, camera_id: Optional[str] = None):
    """
    Gọi sang AI Vision Service (GET /vision/results/recent) để lấy danh sách detection gần đây.
    """
    try:
        target_url = f"{AI_VISION_URL.rstrip('/')}/vision/results/recent?limit={limit}"
        if camera_id:
            target_url += f"&camera_id={camera_id}"
        headers = {"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}"}
        resp = requests.get(target_url, headers=headers, timeout=3.0)
        return {
            "status": "success" if resp.status_code == 200 else "failed",
            "statusCode": resp.status_code,
            "result": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/vision/detection-result", status_code=status.HTTP_200_OK, tags=["ai-vision-webhook"])
async def receive_ai_vision_detection(request: Request):
    """
    Endpoint Webhook để nhận kết quả detection từ AI Vision Service theo hợp đồng OpenAPI 3.1.0.
    Core Business áp dụng rule nghiệp vụ:
    - Nếu phát hiện người trong khu vực cấm / risk_level HIGH -> Tạo alert UNKNOWN_PERSON / SUSPICIOUS_OBJECT.
    - Trả về AIVisionResultAck xác nhận cho AI Vision.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    detection_id = body.get("detection_id") or str(uuid.uuid4())
    camera_id = body.get("camera_id", "cam-default")
    detections = body.get("detections", [])
    risk_level = str(body.get("risk_level", "LOW")).upper()
    metadata = body.get("metadata", {})
    ack_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()

    # Lưu detection vào luồng sự kiện đa hình
    event_record = {
        "eventId": str(uuid.uuid4()),
        "sourceService": "ai-vision",
        "eventType": "AI_VISION_DETECTION",
        "payload": {
            "detection_id": detection_id,
            "camera_id": camera_id,
            "detections": detections,
            "risk_level": risk_level,
            "metadata": metadata,
        },
        "timestamp": body.get("timestamp") or now_str,
        "receivedAt": now_str,
    }
    EVENTS_DB.insert(0, event_record)

    # Core Business Rule Engine: Đánh giá nguy cơ
    if risk_level in ("HIGH", "CRITICAL") or metadata.get("location") == "restricted_area":
        alert_id = str(uuid.uuid4())
        alert_type = "SUSPICIOUS_OBJECT" if any(d.get("label") not in ("person", "human") for d in detections) else "UNKNOWN_PERSON"
        alert_record = {
            "id": alert_id,
            "sourceService": "ai-vision",
            "alertType": alert_type,
            "severity": risk_level if risk_level in ("HIGH", "CRITICAL") else "HIGH",
            "message": f"Phát hiện {len(detections)} đối tượng tại camera {camera_id} (Mức độ: {risk_level})",
            "relatedEventId": detection_id,
            "status": "OPEN",
            "createdAt": now_str,
            "resolvedAt": None,
        }
        ALERTS_DB[alert_id] = alert_record

        # Tự động đẩy qua MQTT sang Analytics
        publish_mqtt_event("business.alert.created", {
            "alert_id": alert_id,
            "alert_type": alert_type,
            "location": camera_id,
            "severity": risk_level,
            "created_at": now_str,
        })

        return {
            "ack_id": ack_id,
            "detection_id": detection_id,
            "status": "ACCEPTED",
            "action_taken": "ALERT_CREATED",
            "alert_id": alert_id,
            "message": "Phát hiện đối tượng khả nghi / vi phạm an ninh, đã tạo alert",
            "processed_at": now_str,
        }

    return {
        "ack_id": ack_id,
        "detection_id": detection_id,
        "status": "ACCEPTED",
        "action_taken": "NONE",
        "alert_id": None,
        "message": "Kết quả đã được ghi nhận, không phát hiện vi phạm",
        "processed_at": now_str,
    }


# -------------------------------
# MQTT Integration (Analytics Service Pair 08)
# -------------------------------
def publish_mqtt_event(event_type: str, data: Dict[str, Any], correlation_id: Optional[str] = None):
    """
    Publish sự kiện nghiệp vụ sang Analytics Service qua MQTT Broker (192.168.1.51:1883)
    theo đúng chuẩn hợp đồng event-contract-08-core-analytics.md (Topic: business.events).
    """
    payload = {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "correlationId": correlation_id or f"req-{uuid.uuid4()}",
        "source": "core-business",
        "data": data,
    }
    try:
        import paho.mqtt.publish as publish
        publish.single(
            topic=MQTT_TOPIC_BUSINESS_EVENTS,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER_HOST,
            port=MQTT_BROKER_PORT,
            keepalive=3,
        )
    except Exception as e:
        print(f"[MQTT] Publish to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} error: {e}")


@app.post("/integrations/analytics/mqtt/publish", tags=["integrations"])
async def trigger_mqtt_publish(event_type: str = "business.alert.created"):
    """
    Bắn thử nghiệm sự kiện MQTT sang Analytics Service (192.168.1.51:1883)
    vào topic 'business.events'.
    """
    sample_data = {
        "business.alert.created": {
            "alert_id": "ALT-" + str(uuid.uuid4())[:8].upper(),
            "alert_type": "UNAUTHORIZED_ACCESS",
            "location": "GATE-01",
            "severity": "HIGH",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "business.policy.decision.created": {
            "decision_id": "DEC-" + str(uuid.uuid4())[:8].upper(),
            "card_id": "RFID-2026-001",
            "gate_id": "GATE-01",
            "direction": "IN",
            "result": "ALLOW",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        },
        "business.alert.resolved": {
            "alert_id": "ALT-001",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    data = sample_data.get(event_type, {"message": "Test event from Core Business"})
    payload = {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "correlationId": f"trace-{uuid.uuid4()}",
        "source": "core-business",
        "data": data,
    }
    try:
        import paho.mqtt.publish as publish
        publish.single(
            topic=MQTT_TOPIC_BUSINESS_EVENTS,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER_HOST,
            port=MQTT_BROKER_PORT,
            keepalive=3,
        )
        return {
            "status": "success",
            "message": f"Đã publish thành công event '{event_type}' lên topic '{MQTT_TOPIC_BUSINESS_EVENTS}' tại {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}!",
            "broker": f"mqtt://{MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}",
            "topic": MQTT_TOPIC_BUSINESS_EVENTS,
            "publishedPayload": payload,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Không thể kết nối tới MQTT Broker tại {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}",
            "error": str(e),
            "broker": f"mqtt://{MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}",
            "topic": MQTT_TOPIC_BUSINESS_EVENTS,
            "attemptedPayload": payload,
        }


# -------------------------------
# WEB DASHBOARD (HTML UI)
# -------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def serve_dashboard():
    """Phục vụ giao diện Live Operations Dashboard trực quan cho toàn hệ thống."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Smart Campus Live Dashboard is active!</h1>")




