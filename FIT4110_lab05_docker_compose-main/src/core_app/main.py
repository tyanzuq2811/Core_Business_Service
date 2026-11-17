import asyncio
import json
import os
import re
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import anyio
import requests
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

try:
    from .storage import create_store
except ImportError:
    from core_app.storage import create_store

# -------------------------------
# Configuration (Plug-a-thon LAN & Docker Compose)
# -------------------------------
SERVICE_NAME = os.getenv("SERVICE_NAME", "core-business")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")
ENV_MODE = os.getenv("ENV", "lan")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "mock-core-token-2026")

# Partner service URLs & tokens (configured via .env or compose overrides)
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
DEFAULT_ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "security-ops@campus.local")

# Core Business Rule thresholds
TEMP_HIGH_THRESHOLD = float(os.getenv("TEMP_HIGH_THRESHOLD", "40.0"))
TEMP_CRITICAL_THRESHOLD = float(os.getenv("TEMP_CRITICAL_THRESHOLD", "50.0"))
ACCESS_RATE_LIMIT_MAX = int(os.getenv("ACCESS_RATE_LIMIT_MAX", "10"))
ENFORCE_TIME_WINDOW = os.getenv("ENFORCE_TIME_WINDOW", "true").lower() == "true"
CAMPUS_TZ_OFFSET_HOURS = int(os.getenv("CAMPUS_TZ_OFFSET_HOURS", "7"))
BLACKLISTED_CARDS = {
    c.strip() for c in os.getenv("BLACKLISTED_CARDS", "RFID-2026-999").split(",") if c.strip()
}

app = FastAPI(
    title="Smart Campus — Core Business Service API",
    version=SERVICE_VERSION,
    description="Core Business Service backend (Dual Storage: PostgreSQL & In-Memory, LAN Plug-a-thon & Compose Mock).",
)

# Khởi tạo lớp lưu trữ kép (PostgreSQL hoặc In-Memory dựa vào STORAGE_BACKEND / DATABASE_URL)
store = create_store()


# -------------------------------
# Error & Auth Helpers
# -------------------------------
def problem_details_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    errors: Optional[List[Dict[str, Any]]] = None,
    type_url: str = "https://campus.local/errors/validation",
) -> JSONResponse:
    """Tạo phản hồi lỗi chuẩn RFC 9457 ProblemDetails."""
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


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None


def _is_authorized(authorization: Optional[str]) -> bool:
    token = _extract_bearer_token(authorization)
    return bool(token and token == AUTH_TOKEN)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors_list = []
    for err in exc.errors():
        field_name = ".".join([str(x) for x in err.get("loc", []) if x not in ("body", "query", "path")])
        errors_list.append(
            {
                "field": field_name or "payload",
                "code": err.get("type", "VALIDATION_ERROR").upper(),
                "message": err.get("msg", "Dữ liệu không hợp lệ"),
            }
        )
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


class NotificationDispatchPayload(BaseModel):
    recipient: str = DEFAULT_ALERT_RECIPIENT
    channel: str = "EMAIL"
    subject: str
    message: str
    severity: str = "HIGH"


# -------------------------------
# Outbound Helpers (MQTT & Notification & Partner Proxy)
# -------------------------------
def publish_mqtt_event(event_type: str, data: Dict[str, Any], correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Publish sự kiện nghiệp vụ sang Analytics Service qua MQTT Broker
    theo chuẩn hợp đồng event-contract-08-core-analytics.md (Topic: business.events).
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
        # Fail-fast TCP reachability check so offline MQTT never stalls background task queues
        with socket.create_connection((MQTT_BROKER_HOST, MQTT_BROKER_PORT), timeout=0.5):
            pass

        import paho.mqtt.publish as publish

        publish.single(
            topic=MQTT_TOPIC_BUSINESS_EVENTS,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER_HOST,
            port=MQTT_BROKER_PORT,
            keepalive=2,
        )
        return {"status": "success", "payload": payload}
    except Exception as exc:
        print(f"[MQTT] Publish to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} error: {exc}")
        return {"status": "error", "error": str(exc), "payload": payload}


def dispatch_notification(
    subject: str,
    message: str,
    severity: str = "HIGH",
    recipient: str = DEFAULT_ALERT_RECIPIENT,
    channel: str = "EMAIL",
) -> Dict[str, Any]:
    """Đẩy thông báo cảnh báo tới Notification Service (POST /notifications/send)."""
    target_url = f"{NOTIFICATION_SERVICE_URL.rstrip('/')}/notifications/send"
    body = {
        "recipient": recipient,
        "channel": channel,
        "subject": subject,
        "message": message,
        "severity": severity,
    }
    try:
        resp = requests.post(target_url, json=body, timeout=2.0)
        parsed = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"raw": resp.text}
        return {
            "status": "success" if resp.status_code in (200, 201, 202) else "failed",
            "statusCode": resp.status_code,
            "url": target_url,
            "response": parsed,
        }
    except Exception as exc:
        print(f"[NOTIFY] Dispatch to {target_url} error: {exc}")
        return {"status": "error", "url": target_url, "error": str(exc)}


def dispatch_alert_side_effects(alert: Dict[str, Any], location: str = "GATE-01", correlation_id: Optional[str] = None) -> None:
    """Tác vụ nền: gửi Notification (nếu HIGH/CRITICAL) trước, sau đó publish MQTT event."""
    if str(alert.get("severity", "")).upper() in ("HIGH", "CRITICAL"):
        dispatch_notification(
            subject=f"[{alert['severity']}] Smart Campus Alert: {alert['alertType']}",
            message=alert["message"],
            severity=alert["severity"],
        )
    publish_mqtt_event(
        "business.alert.created",
        {
            "alert_id": alert["id"],
            "alert_type": alert["alertType"],
            "location": location,
            "severity": alert["severity"],
            "created_at": alert["createdAt"],
        },
        correlation_id=correlation_id,
    )


def _proxy_partner_request(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 3.0,
) -> Dict[str, Any]:
    """Helper gọi HTTP đồng nhất sang các partner service trong mạng LAN / Docker network."""
    try:
        resp = requests.request(method=method, url=url, headers=headers, json=json_body, timeout=timeout)
        content_type = resp.headers.get("content-type", "")
        parsed = resp.json() if "application/json" in content_type else {"raw": resp.text[:300]}
        return {
            "status": "success" if 200 <= resp.status_code < 300 else "failed",
            "statusCode": resp.status_code,
            "url": url,
            "body": parsed,
        }
    except Exception as exc:
        return {
            "status": "error",
            "url": url,
            "error": str(exc),
        }


# -------------------------------
# Rule Evaluation Helpers
# -------------------------------
def _parse_access_timestamp(ts: Optional[str]) -> datetime:
    campus_tz = timezone(timedelta(hours=CAMPUS_TZ_OFFSET_HOURS))
    if not ts:
        return datetime.now(campus_tz)
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=campus_tz)
        return parsed
    except ValueError:
        return datetime.now(campus_tz)


def _is_within_time_window(dt: datetime, start_str: str, end_str: str) -> bool:
    sh, sm = (int(x) for x in start_str.split(":"))
    eh, em = (int(x) for x in end_str.split(":"))
    minutes = dt.hour * 60 + dt.minute
    start_m = sh * 60 + sm
    end_m = eh * 60 + em
    return start_m <= minutes <= end_m


def _evaluate_access_policy(payload: AccessCheckPayload) -> Dict[str, Any]:
    """Đánh giá chính sách POL-001 (allowedGates, blacklist, timeWindow, rapid-swipe rate limit)."""
    policy = store.get_policy("POL-001") or {}
    conditions = policy.get("conditions") or {}
    allowed_gates = policy.get("allowedGates") or conditions.get("allowedGates") or ["GATE-01", "GATE-02"]
    time_window = policy.get("timeWindow") or {"start": "06:00", "end": "22:00"}

    if payload.cardId in BLACKLISTED_CARDS:
        return {"result": "DENY", "reasonCode": "BLACKLISTED", "policyId": "POL-001"}

    if payload.gateId not in allowed_gates:
        return {"result": "DENY", "reasonCode": "POLICY_DENY", "policyId": "POL-001"}

    if ENFORCE_TIME_WINDOW:
        check_dt = _parse_access_timestamp(payload.timestamp)
        if not _is_within_time_window(check_dt, time_window.get("start", "06:00"), time_window.get("end", "22:00")):
            return {"result": "DENY", "reasonCode": "OUTSIDE_TIME_WINDOW", "policyId": "POL-001"}

    recent_swipes = store.count_recent_decisions_for_card(payload.cardId, window_seconds=60)
    if recent_swipes >= ACCESS_RATE_LIMIT_MAX:
        return {"result": "DENY", "reasonCode": "POLICY_DENY", "policyId": "POL-001"}

    return {"result": "ALLOW", "reasonCode": "VALID_CARD", "policyId": "POL-001"}


# -------------------------------
# Core Business API Endpoints
# -------------------------------
@app.get("/health", tags=["health"])
async def get_health():
    db_health = store.health_check()
    return {
        "status": "ok" if db_health.get("status") == "ok" else "degraded",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "storage": store.backend_name,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/alerts", status_code=status.HTTP_201_CREATED, tags=["alerts"])
async def create_alert(
    payload: AlertCreatePayload,
    request: Request,
    background_tasks: BackgroundTasks,
    prefer: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    if prefer == "code=400":
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Payload không đúng JSON Schema, thiếu trường bắt buộc sourceService",
            instance=str(request.url.path),
            errors=[{"field": "sourceService", "code": "REQUIRED", "message": "Trường sourceService là bắt buộc"}],
        )
    if prefer == "code=500":
        return problem_details_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
            detail="Đã xảy ra sự cố nội bộ trên máy chủ Core Business",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/server-error",
        )

    if not _is_authorized(authorization):
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
        "relatedEventId": payload.relatedEventId,
        "status": "OPEN",
        "createdAt": now_str,
        "resolvedAt": None,
    }
    store.create_alert(new_alert)
    background_tasks.add_task(dispatch_alert_side_effects, new_alert, "GATE-01")
    return new_alert


@app.get("/alerts", tags=["alerts"])
async def list_alerts(
    request: Request,
    limit: int = 10,
    prefer: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    # Nếu client chủ động gửi Authorization header sai thì từ chối 401; Dashboard nội bộ không gửi header vẫn đọc được
    if authorization is not None and not _is_authorized(authorization):
        return problem_details_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Bearer Token không hợp lệ",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/unauthorized",
        )

    if prefer == "code=400" or limit < 1 or limit > 100:
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Tham số không hợp lệ",
            detail="Tham số limit phải có giá trị trong khoảng từ 1 đến 100",
            instance=str(request.url.path),
        )

    items, total = store.list_alerts(limit)
    return {
        "items": items,
        "nextCursor": None,
        "hasMore": total > limit,
        "total": total,
    }


@app.get("/alerts/recent", tags=["alerts"])
async def get_recent_alerts(limit: int = 5):
    return {"items": store.get_recent_alerts(limit)}


@app.get("/alerts/{alert_id}", tags=["alerts"])
async def get_alert_detail(
    alert_id: str,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    alert = None if prefer == "code=404" else store.get_alert(alert_id)
    if alert is None:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy cảnh báo với alertId '{alert_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    return alert


@app.post("/alerts/{alert_id}/resolve", tags=["alerts"])
async def resolve_alert(
    alert_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Đánh dấu cảnh báo đã được giải quyết (RESOLVED)."""
    resolved_at = datetime.now(timezone.utc).isoformat()
    resolved = store.resolve_alert(alert_id, resolved_at)
    if resolved is None:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy cảnh báo với alertId '{alert_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    background_tasks.add_task(
        publish_mqtt_event,
        "business.alert.resolved",
        {"alert_id": alert_id, "resolved_at": resolved_at},
    )
    return resolved


@app.get("/decisions", tags=["access-policy"])
async def list_decisions():
    """Lấy danh sách quyết định quẹt thẻ phục vụ Dashboard & Analytics."""
    return store.list_decisions()


@app.get("/events", tags=["events"])
async def list_events():
    """Lấy danh sách sự kiện đã tiếp nhận phục vụ Dashboard."""
    return store.list_events()


@app.post("/dashboard/clear-data", tags=["dashboard"])
async def clear_live_data():
    """Làm sạch dữ liệu nghiệp vụ trong Store hiện tại để demo sạch từ đầu."""
    store.clear_data()
    return {
        "status": "ok",
        "storage": store.backend_name,
        "message": f"Đã làm sạch toàn bộ dữ liệu ({store.backend_name})! Sẵn sàng tiếp nhận dữ liệu thật.",
    }


@app.post("/access/check", tags=["access-policy"])
async def check_access(
    payload: AccessCheckPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    prefer: Optional[str] = Header(None),
):
    card_pattern = r"^RFID-[0-9]{4}-[0-9]{3}$"
    if prefer == "code=400" or not re.match(card_pattern, payload.cardId):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Trường cardId không đúng định dạng RFID-YYYY-NNN",
            instance=str(request.url.path),
            errors=[{"field": "cardId", "code": "PATTERN_MISMATCH", "message": "cardId phải có dạng RFID-YYYY-NNN"}],
        )

    gate_pattern = r"^GATE-[0-9]{2}$"
    if not re.match(gate_pattern, payload.gateId):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Trường gateId phải có định dạng GATE-XX (ví dụ: GATE-01)",
            instance=str(request.url.path),
            errors=[{"field": "gateId", "code": "PATTERN_MISMATCH", "message": "gateId phải có dạng GATE-XX"}],
        )

    if payload.direction not in ("IN", "OUT"):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Trường direction phải là IN hoặc OUT",
            instance=str(request.url.path),
            errors=[{"field": "direction", "code": "INVALID_ENUM", "message": "direction phải là IN hoặc OUT"}],
        )

    if prefer == "code=409" or (payload.idempotencyKey and store.has_idempotency_key(payload.idempotencyKey)):
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Xung đột trùng lặp giao dịch",
            detail=f"IdempotencyKey '{payload.idempotencyKey}' đã được xử lý trước đó",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/conflict",
        )

    evaluation = _evaluate_access_policy(payload)
    decision_id = str(uuid.uuid4())
    evaluated_at = datetime.now(timezone.utc).isoformat()
    decision = {
        "decisionId": decision_id,
        "cardId": payload.cardId,
        "gateId": payload.gateId,
        "direction": payload.direction,
        "result": evaluation["result"],
        "reasonCode": evaluation["reasonCode"],
        "policyId": evaluation["policyId"],
        "evaluatedAt": evaluated_at,
        "expiresAt": None,
    }
    store.create_decision(decision)
    if payload.idempotencyKey:
        store.save_idempotency_key(payload.idempotencyKey)

    if evaluation["result"] == "DENY":
        deny_alert = {
            "id": str(uuid.uuid4()),
            "sourceService": "core-business",
            "alertType": "UNAUTHORIZED_ACCESS",
            "severity": "HIGH",
            "message": f"Từ chối truy cập thẻ {payload.cardId} tại {payload.gateId} ({evaluation['reasonCode']})",
            "relatedEventId": decision_id,
            "status": "OPEN",
            "createdAt": evaluated_at,
            "resolvedAt": None,
        }
        store.create_alert(deny_alert)
        background_tasks.add_task(dispatch_alert_side_effects, deny_alert, payload.gateId, payload.idempotencyKey)

    background_tasks.add_task(
        publish_mqtt_event,
        "business.policy.decision.created",
        {
            "decision_id": decision_id,
            "policy_type": "ACCESS",
            "decision": evaluation["result"],
            "location": payload.gateId,
            "subject_type": "STUDENT",
            "decided_at": evaluated_at,
            "card_id": payload.cardId,
            "gate_id": payload.gateId,
            "direction": payload.direction,
            "result": evaluation["result"],
            "reason_code": evaluation["reasonCode"],
        },
        payload.idempotencyKey,
    )

    return decision


@app.get("/policies/access/{policy_id}", tags=["access-policy"])
async def get_policy_detail(
    policy_id: str,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    policy = None if prefer == "code=404" else store.get_policy(policy_id)
    if policy is None:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy Policy với policyId '{policy_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    return policy


@app.get("/decisions/{decision_id}", tags=["access-policy"])
async def get_decision_detail(
    decision_id: str,
    request: Request,
    prefer: Optional[str] = Header(None),
):
    decision = None if prefer == "code=404" else store.get_decision(decision_id)
    if decision is None:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tài nguyên không tồn tại",
            detail=f"Không tìm thấy Quyết định với decisionId '{decision_id}'",
            instance=str(request.url.path),
            type_url="https://campus.local/errors/not-found",
        )
    return decision


@app.post("/events", status_code=status.HTTP_201_CREATED, tags=["events"])
async def ingest_event(request: Request, background_tasks: BackgroundTasks):
    """
    Tiếp nhận sự kiện từ IoT Ingestion hoặc các phân hệ khác theo chuẩn OpenAPI contract.
    Hỗ trợ payload lồng `data`/`payload` ({metric, value}) và payload phẳng ({temperature, humidity, motion}).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    if not isinstance(body, dict):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Event body phải là JSON object",
            instance=str(request.url.path),
        )

    event_id = body.get("eventId") or str(uuid.uuid4())
    event_type = body.get("eventType") or "sensor.reading.created"
    source = body.get("source") or body.get("sourceService") or "iot-ingestion"
    now_str = datetime.now(timezone.utc).isoformat()
    occurred_at = body.get("occurredAt") or body.get("timestamp") or now_str
    correlation_id = body.get("correlationId")

    data_payload = body.get("data") or body.get("payload") or {}
    if not data_payload:
        flat_keys = ("deviceId", "sensorId", "metric", "value", "unit", "locationId", "temperature", "humidity", "motion", "gasPpm")
        if any(k in body for k in flat_keys):
            data_payload = {k: body[k] for k in flat_keys if k in body}

    event_record = {
        "eventId": event_id,
        "sourceService": source,
        "eventType": event_type,
        "correlationId": correlation_id,
        "payload": data_payload,
        "timestamp": occurred_at,
        "receivedAt": now_str,
    }
    store.create_event(event_record)

    metric = data_payload.get("metric")
    val = data_payload.get("value")
    if metric is None and "temperature" in data_payload:
        metric = "temperature"
        val = data_payload.get("temperature")

    is_overheat = (
        event_type == "sensor.threshold.exceeded"
        or (metric == "temperature" and isinstance(val, (int, float)) and val > TEMP_HIGH_THRESHOLD)
    )
    if is_overheat:
        is_critical = isinstance(val, (int, float)) and val > TEMP_CRITICAL_THRESHOLD
        device_label = data_payload.get("deviceId") or data_payload.get("sensorId") or "SENSOR"
        loc_label = data_payload.get("locationId") or "Campus"
        alert_record = {
            "id": str(uuid.uuid4()),
            "sourceService": source,
            "alertType": "SENSOR_THRESHOLD_EXCEEDED",
            "severity": "CRITICAL" if is_critical else "HIGH",
            "message": f"Cảm biến {device_label} tại {loc_label} đo được {val}°C (vượt ngưỡng {TEMP_HIGH_THRESHOLD}°C)!",
            "relatedEventId": event_id,
            "status": "OPEN",
            "createdAt": now_str,
            "resolvedAt": None,
        }
        store.create_alert(alert_record)
        background_tasks.add_task(dispatch_alert_side_effects, alert_record, loc_label, correlation_id)

    return {
        "eventId": event_id,
        "acceptedAt": now_str,
    }


# -------------------------------
# Plug-a-thon LAN & Mock Compose Integrations
# -------------------------------
def ping_service(service_name: str, base_url: str) -> Dict[str, Any]:
    """Kiểm tra kết nối /health tới 1 partner service với timeout ngắn 1.5s."""
    target_url = f"{base_url.rstrip('/')}/health"
    try:
        start_time = datetime.now()
        resp = requests.get(target_url, timeout=1.5)
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        is_ok = resp.status_code in (200, 201)
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
    except Exception as exc:
        return {
            "service": service_name,
            "url": base_url,
            "status": "OFFLINE",
            "statusCode": None,
            "latencyMs": None,
            "error": str(exc),
        }


def _partner_map() -> Dict[str, str]:
    return {
        "ai-vision": AI_VISION_URL,
        "iot-ingestion": IOT_SERVICE_URL,
        "access-gate": GATE_SERVICE_URL,
        "analytics": ANALYTICS_SERVICE_URL,
        "notification": NOTIFICATION_SERVICE_URL,
    }


@app.get("/integrations/config", tags=["integrations"])
async def get_integration_config():
    """Trả về cấu hình đối tác & storage hiện hành để Dashboard hiển thị động (không chứa secret)."""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "env": ENV_MODE,
        "storageBackend": store.backend_name,
        "storageHealth": store.health_check(),
        "authConfigured": bool(AUTH_TOKEN),
        "partners": _partner_map(),
        "mqtt": {
            "host": MQTT_BROKER_HOST,
            "port": MQTT_BROKER_PORT,
            "topic": MQTT_TOPIC_BUSINESS_EVENTS,
        },
        "thresholds": {
            "temperatureHigh": TEMP_HIGH_THRESHOLD,
            "temperatureCritical": TEMP_CRITICAL_THRESHOLD,
            "accessRateLimitPerMin": ACCESS_RATE_LIMIT_MAX,
        },
    }


@app.get("/integrations/status", tags=["integrations"])
async def check_all_lan_integrations():
    """Kiểm tra đồng thời trạng thái /health của toàn bộ 5 dịch vụ đối tác qua thread pool."""
    services_to_check = _partner_map()
    tasks = [anyio.to_thread.run_sync(ping_service, name, url) for name, url in services_to_check.items()]
    checked = await asyncio.gather(*tasks)

    results = {item["service"]: item for item in checked}
    online_count = sum(1 for item in checked if item["status"] == "ONLINE")

    return {
        "summary": {
            "coreBusinessVersion": SERVICE_VERSION,
            "storageBackend": store.backend_name,
            "totalPartners": len(services_to_check),
            "onlinePartners": online_count,
            "offlinePartners": len(services_to_check) - online_count,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
        },
        "partners": results,
    }


@app.get("/integrations/{service_name}/health", tags=["integrations"])
async def check_single_service_health(service_name: str):
    """Kiểm tra kết nối trực tiếp đến 1 service cụ thể."""
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
            detail=f"Service '{service_name}' không hợp lệ. Các service hỗ trợ: {list(service_map.keys())}",
        )
    return await anyio.to_thread.run_sync(ping_service, service_name, service_map[service_name])


@app.get("/integrations/gate/cards/{card_id}", tags=["integrations"])
async def get_gate_card_info(card_id: str):
    """Gọi sang Access Gate Service (/cards/{cardId}) với Bearer token."""
    target_url = f"{GATE_SERVICE_URL.rstrip('/')}/cards/{card_id}"
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("GET", target_url, headers={"Authorization": f"Bearer {GATE_AUTH_TOKEN}"})
    )
    if res["status"] == "error":
        return {"status": "error", "gateUrl": target_url, "error": res["error"]}
    return {
        "status": res["status"],
        "gateUrl": target_url,
        "statusCode": res["statusCode"],
        "cardId": card_id,
        "data": res["body"],
    }


@app.get("/integrations/gate/logs/recent", tags=["integrations"])
async def get_gate_recent_logs(limit: int = 5):
    """Gọi sang Access Gate Service (GET /access/logs/recent)."""
    target_url = f"{GATE_SERVICE_URL.rstrip('/')}/access/logs/recent?limit={limit}"
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("GET", target_url, headers={"Authorization": f"Bearer {GATE_AUTH_TOKEN}"})
    )
    if res["status"] == "error":
        return {"status": "error", "gateUrl": target_url, "error": res["error"]}
    return {"status": res["status"], "gateUrl": target_url, "statusCode": res["statusCode"], "logs": res["body"]}


@app.get("/integrations/gate/gates/{gate_id}/status", tags=["integrations"])
async def get_gate_barrier_status(gate_id: str = "GATE-01"):
    """Gọi sang Access Gate Service (GET /gates/{gateId}/status)."""
    target_url = f"{GATE_SERVICE_URL.rstrip('/')}/gates/{gate_id}/status"
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("GET", target_url, headers={"Authorization": f"Bearer {GATE_AUTH_TOKEN}"})
    )
    if res["status"] == "error":
        return {"status": "error", "gateUrl": target_url, "error": res["error"]}
    return {
        "status": res["status"],
        "gateUrl": target_url,
        "statusCode": res["statusCode"],
        "gateId": gate_id,
        "data": res["body"],
    }


@app.post("/integrations/ai-vision/face-match", tags=["integrations"])
async def test_ai_vision_face_match(payload: Optional[Dict[str, Any]] = None):
    """Gọi sang AI Vision Service (POST /vision/face-match)."""
    target_url = f"{AI_VISION_URL.rstrip('/')}/vision/face-match"
    headers = {"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}", "Content-Type": "application/json"}
    body = payload or {
        "image_url": "http://storage.campus.local/cameras/cam-gate-01/frames/latest.jpg",
        "reference_image_url": "http://storage.campus.local/profiles/student-001.jpg",
        "threshold": 0.75,
        "trace_id": f"trace-core-{int(datetime.now().timestamp())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("POST", target_url, headers=headers, json_body=body, timeout=4.0)
    )
    if res["status"] == "error":
        return {"status": "error", "error": res["error"]}
    return {"status": res["status"], "statusCode": res["statusCode"], "result": res["body"]}


@app.get("/integrations/ai-vision/models", tags=["integrations"])
async def test_ai_vision_models():
    """Gọi sang AI Vision Service (GET /vision/models/info)."""
    target_url = f"{AI_VISION_URL.rstrip('/')}/vision/models/info"
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("GET", target_url, headers={"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}"})
    )
    if res["status"] == "error":
        return {"status": "error", "error": res["error"]}
    return {"status": res["status"], "statusCode": res["statusCode"], "modelInfo": res["body"]}


@app.post("/integrations/ai-vision/detect", tags=["integrations"])
async def test_ai_vision_detect(payload: Optional[Dict[str, Any]] = None):
    """Gọi sang AI Vision Service (POST /vision/detect)."""
    target_url = f"{AI_VISION_URL.rstrip('/')}/vision/detect"
    headers = {"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}", "Content-Type": "application/json"}
    body = payload or {
        "camera_id": "cam-gate-01",
        "image_url": "http://storage.campus.local/images/frame-20260811-001.jpg",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence_threshold": 0.6,
    }
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("POST", target_url, headers=headers, json_body=body, timeout=4.0)
    )
    if res["status"] == "error":
        return {"status": "error", "error": res["error"]}
    return {"status": res["status"], "statusCode": res["statusCode"], "result": res["body"]}


@app.get("/integrations/ai-vision/detections/{detection_id}", tags=["integrations"])
async def get_ai_vision_detection_by_id(detection_id: str):
    """Gọi sang AI Vision Service (GET /vision/detections/{detectionId})."""
    target_url = f"{AI_VISION_URL.rstrip('/')}/vision/detections/{detection_id}"
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("GET", target_url, headers={"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}"})
    )
    if res["status"] == "error":
        return {"status": "error", "error": res["error"]}
    return {"status": res["status"], "statusCode": res["statusCode"], "detectionId": detection_id, "result": res["body"]}


@app.get("/integrations/ai-vision/results/recent", tags=["integrations"])
async def get_ai_vision_recent_results(limit: int = 10, camera_id: Optional[str] = None):
    """Gọi sang AI Vision Service (GET /vision/results/recent)."""
    target_url = f"{AI_VISION_URL.rstrip('/')}/vision/results/recent?limit={limit}"
    if camera_id:
        target_url += f"&camera_id={camera_id}"
    res = await anyio.to_thread.run_sync(
        lambda: _proxy_partner_request("GET", target_url, headers={"Authorization": f"Bearer {AI_VISION_AUTH_TOKEN}"})
    )
    if res["status"] == "error":
        return {"status": "error", "error": res["error"]}
    return {"status": res["status"], "statusCode": res["statusCode"], "result": res["body"]}


@app.post("/integrations/notification/send", tags=["integrations"])
async def trigger_notification_send(payload: NotificationDispatchPayload):
    """Gửi thông báo trực tiếp qua Notification Service (POST /notifications/send)."""
    return await anyio.to_thread.run_sync(
        lambda: dispatch_notification(
            subject=payload.subject,
            message=payload.message,
            severity=payload.severity,
            recipient=payload.recipient,
            channel=payload.channel,
        )
    )


@app.post("/vision/detection-result", status_code=status.HTTP_200_OK, tags=["ai-vision-webhook"])
async def receive_ai_vision_detection(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint Webhook nhận kết quả detection từ AI Vision Service theo OpenAPI 3.1.0.
    Nếu phát hiện đối tượng nguy cơ cao hoặc tại restricted_area -> tự động tạo Alert + gửi MQTT & Notification.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    if not isinstance(body, dict) or not body.get("camera_id"):
        return problem_details_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ về nghiệp vụ",
            detail="Webhook /vision/detection-result yêu cầu trường camera_id",
            instance=str(request.url.path),
            errors=[{"field": "camera_id", "code": "REQUIRED", "message": "camera_id là bắt buộc"}],
        )

    detection_id = body.get("detection_id") or str(uuid.uuid4())
    camera_id = body["camera_id"]
    detections = body.get("detections", [])
    risk_level = str(body.get("risk_level", "LOW")).upper()
    metadata = body.get("metadata", {})
    ack_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()

    event_record = {
        "eventId": str(uuid.uuid4()),
        "sourceService": "ai-vision",
        "eventType": "AI_VISION_DETECTION",
        "correlationId": detection_id,
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
    store.create_event(event_record)

    if risk_level in ("HIGH", "CRITICAL") or metadata.get("location") == "restricted_area":
        alert_id = str(uuid.uuid4())
        alert_type = (
            "SUSPICIOUS_OBJECT"
            if any(d.get("label") not in ("person", "human") for d in detections if isinstance(d, dict))
            else "UNKNOWN_PERSON"
        )
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
        store.create_alert(alert_record)
        background_tasks.add_task(dispatch_alert_side_effects, alert_record, camera_id, detection_id)

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


@app.post("/integrations/analytics/mqtt/publish", tags=["integrations"])
async def trigger_mqtt_publish(event_type: str = "business.alert.created"):
    """Bắn thử nghiệm sự kiện MQTT sang Analytics Service vào topic 'business.events'."""
    now_str = datetime.now(timezone.utc).isoformat()
    sample_data = {
        "business.alert.created": {
            "alert_id": "ALT-" + str(uuid.uuid4())[:8].upper(),
            "alert_type": "UNAUTHORIZED_ACCESS",
            "location": "GATE-01",
            "severity": "HIGH",
            "created_at": now_str,
        },
        "business.policy.decision.created": {
            "decision_id": "DEC-" + str(uuid.uuid4())[:8].upper(),
            "policy_type": "ACCESS",
            "decision": "ALLOW",
            "location": "GATE-01",
            "subject_type": "STUDENT",
            "decided_at": now_str,
            "card_id": "RFID-2026-001",
            "gate_id": "GATE-01",
            "direction": "IN",
            "result": "ALLOW",
            "evaluated_at": now_str,
        },
        "business.alert.resolved": {
            "alert_id": "ALT-001",
            "resolved_at": now_str,
        },
    }
    data = sample_data.get(event_type, {"message": "Test event from Core Business"})
    res = await anyio.to_thread.run_sync(lambda: publish_mqtt_event(event_type, data))
    if res["status"] == "success":
        return {
            "status": "success",
            "message": f"Đã publish thành công event '{event_type}' lên topic '{MQTT_TOPIC_BUSINESS_EVENTS}' tại {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}!",
            "broker": f"mqtt://{MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}",
            "topic": MQTT_TOPIC_BUSINESS_EVENTS,
            "publishedPayload": res["payload"],
        }
    return {
        "status": "error",
        "message": f"Không thể kết nối tới MQTT Broker tại {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}",
        "error": res.get("error"),
        "broker": f"mqtt://{MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}",
        "topic": MQTT_TOPIC_BUSINESS_EVENTS,
        "attemptedPayload": res["payload"],
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
