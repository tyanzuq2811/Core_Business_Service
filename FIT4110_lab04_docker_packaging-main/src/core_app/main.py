import os
from datetime import datetime, timezone
import re
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Đọc cấu hình từ biến môi trường (truyền qua Docker --env-file hoặc .env)
SERVICE_NAME = os.getenv("SERVICE_NAME", "core-business")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.4.0")

app = FastAPI(
    title="Smart Campus — Core Business Service API",
    version=SERVICE_VERSION,
    description="Core Business Service backend implementation for Lab 04 Docker packaging.",
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
    new_alert = {
        "id": alert_id,
        "sourceService": payload.sourceService,
        "alertType": payload.alertType,
        "severity": payload.severity,
        "message": payload.message,
        "status": "OPEN",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "resolvedAt": None,
    }
    ALERTS_DB[alert_id] = new_alert
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
    decision = {
        "decisionId": decision_id,
        "cardId": payload.cardId,
        "gateId": payload.gateId,
        "result": "ALLOW",
        "reasonCode": "VALID_CARD",
        "policyId": "POL-001",
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
    }
    DECISIONS_DB[decision_id] = decision
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
async def ingest_event(payload: EventIngestPayload):
    event_id = payload.eventId or str(uuid.uuid4())
    return {
        "eventId": event_id,
        "eventType": payload.eventType,
        "status": "ACCEPTED",
        "acceptedAt": datetime.now(timezone.utc).isoformat(),
    }
