"""Dual storage layer for Core Business Service (PostgreSQL & In-Memory).

Chế độ mặc định chọn theo biến môi trường STORAGE_BACKEND:
- "postgres": Lưu trữ bền vững vào PostgreSQL (khi chạy Docker Compose)
- "memory":   Lưu trữ tạm trên RAM (khi chạy local không cần PostgreSQL)
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
import threading
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_alerts() -> Dict[str, Dict[str, Any]]:
    return {
        "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc": {
            "id": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
            "sourceService": "core-business",
            "alertType": "UNAUTHORIZED_ACCESS",
            "severity": "HIGH",
            "message": "Phát hiện truy cập trái phép tại cổng chính",
            "relatedEventId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
            "status": "OPEN",
            "createdAt": "2026-05-10T08:00:00Z",
            "resolvedAt": None,
        }
    }


def default_policies() -> Dict[str, Dict[str, Any]]:
    return {
        "POL-001": {
            "policyId": "POL-001",
            "name": "Default Student Campus Access",
            "effect": "ALLOW",
            "status": "ACTIVE",
            "description": "Cho phép truy cập cổng chính trong khung giờ 06:00-22:00",
            "timeWindow": {"start": "06:00", "end": "22:00"},
            "allowedGates": ["GATE-01", "GATE-02"],
            "conditions": {"allowedGates": ["GATE-01", "GATE-02"], "timeWindow": "06:00-22:00"},
            "active": True,
        }
    }


def default_decisions() -> Dict[str, Dict[str, Any]]:
    return {
        "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002": {
            "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
            "cardId": "RFID-2026-001",
            "gateId": "GATE-01",
            "direction": "IN",
            "result": "ALLOW",
            "reasonCode": "VALID_CARD",
            "policyId": "POL-001",
            "evaluatedAt": "2026-05-10T08:00:00Z",
            "expiresAt": None,
        }
    }


def default_events() -> List[Dict[str, Any]]:
    return [
        {
            "eventId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2e001",
            "sourceService": "iot-ingestion",
            "eventType": "SENSOR_TELEMETRY",
            "correlationId": None,
            "payload": {"sensorId": "ENV-01", "temperature": 24.5, "humidity": 65.0},
            "timestamp": "2026-08-27T07:10:00Z",
            "receivedAt": "2026-08-27T07:10:00Z",
        },
        {
            "eventId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2e002",
            "sourceService": "ai-vision",
            "eventType": "OBJECT_DETECTION",
            "correlationId": None,
            "payload": {"cameraId": "cam-gate-01", "detectedObjects": ["person", "car"], "confidence": 0.94},
            "timestamp": "2026-08-27T07:12:00Z",
            "receivedAt": "2026-08-27T07:12:00Z",
        },
    ]


class BaseStore:
    """Giao diện lưu trữ chung cho InMemoryStore và PostgresStore."""

    backend_name: str = "base"

    def list_alerts(self, limit: int) -> tuple[List[Dict[str, Any]], int]:
        raise NotImplementedError

    def get_recent_alerts(self, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def create_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def resolve_alert(self, alert_id: str, resolved_at: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def list_decisions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def create_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def count_recent_decisions_for_card(self, card_id: str, window_seconds: int = 60) -> int:
        raise NotImplementedError

    def has_idempotency_key(self, key: str) -> bool:
        raise NotImplementedError

    def save_idempotency_key(self, key: str) -> None:
        raise NotImplementedError

    def list_events(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def create_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def clear_data(self) -> None:
        raise NotImplementedError

    def health_check(self) -> Dict[str, Any]:
        return {"backend": self.backend_name, "status": "ok"}


class InMemoryStore(BaseStore):
    """Lưu trữ trên RAM (phù hợp chạy độc lập hoặc kiểm thử nhanh)."""

    backend_name = "memory"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.alerts: Dict[str, Dict[str, Any]] = default_alerts()
        self.policies: Dict[str, Dict[str, Any]] = default_policies()
        self.decisions: Dict[str, Dict[str, Any]] = default_decisions()
        self.events: List[Dict[str, Any]] = default_events()
        self.idempotency_keys: set[str] = set()

    def list_alerts(self, limit: int) -> tuple[List[Dict[str, Any]], int]:
        with self._lock:
            all_items = list(reversed(list(self.alerts.values())))
            return deepcopy(all_items[:limit]), len(all_items)

    def get_recent_alerts(self, limit: int) -> List[Dict[str, Any]]:
        items, _ = self.list_alerts(limit)
        return items

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self.alerts.get(alert_id)
            return deepcopy(item) if item else None

    def create_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self.alerts[alert["id"]] = deepcopy(alert)
            return deepcopy(alert)

    def resolve_alert(self, alert_id: str, resolved_at: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self.alerts.get(alert_id)
            if not item:
                return None
            item["status"] = "RESOLVED"
            item["resolvedAt"] = resolved_at
            return deepcopy(item)

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self.policies.get(policy_id)
            return deepcopy(item) if item else None

    def list_decisions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(list(reversed(list(self.decisions.values()))))

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self.decisions.get(decision_id)
            return deepcopy(item) if item else None

    def create_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self.decisions[decision["decisionId"]] = deepcopy(decision)
            return deepcopy(decision)

    def count_recent_decisions_for_card(self, card_id: str, window_seconds: int = 60) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        count = 0
        with self._lock:
            for item in self.decisions.values():
                if item.get("cardId") != card_id:
                    continue
                raw_ts = item.get("evaluatedAt")
                if not raw_ts:
                    continue
                try:
                    dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt >= cutoff:
                        count += 1
                except ValueError:
                    continue
        return count

    def has_idempotency_key(self, key: str) -> bool:
        with self._lock:
            return key in self.idempotency_keys

    def save_idempotency_key(self, key: str) -> None:
        with self._lock:
            self.idempotency_keys.add(key)

    def list_events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self.events)

    def create_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self.events.insert(0, deepcopy(event))
            return deepcopy(event)

    def clear_data(self) -> None:
        now = _now_iso()
        with self._lock:
            self.events.clear()
            self.idempotency_keys.clear()
            self.alerts = {
                "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc": {
                    "id": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
                    "sourceService": "core-business",
                    "alertType": "SYSTEM_READY",
                    "severity": "LOW",
                    "message": "Hệ thống sẵn sàng tiếp nhận dữ liệu thật từ các nhóm mạng LAN",
                    "relatedEventId": None,
                    "status": "OPEN",
                    "createdAt": now,
                    "resolvedAt": None,
                }
            }
            self.decisions = {
                "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002": {
                    "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
                    "cardId": "RFID-2026-001",
                    "gateId": "GATE-01",
                    "direction": "IN",
                    "result": "ALLOW",
                    "reasonCode": "VALID_CARD",
                    "policyId": "POL-001",
                    "evaluatedAt": now,
                    "expiresAt": None,
                }
            }


class PostgresStore(BaseStore):
    """Lưu trữ bền vững bằng PostgreSQL 15 (tự tạo bảng & seed dữ liệu ban đầu)."""

    backend_name = "postgres"

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._ensure_schema_and_seed()

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url, connect_timeout=3)

    def _ensure_schema_and_seed(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        id TEXT PRIMARY KEY,
                        source_service TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        related_event_id TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        resolved_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS policies (
                        policy_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        effect TEXT NOT NULL,
                        status TEXT NOT NULL,
                        description TEXT,
                        time_window_json TEXT NOT NULL,
                        allowed_gates_json TEXT NOT NULL,
                        conditions_json TEXT NOT NULL,
                        active BOOLEAN NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS decisions (
                        decision_id TEXT PRIMARY KEY,
                        card_id TEXT NOT NULL,
                        gate_id TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        result TEXT NOT NULL,
                        reason_code TEXT NOT NULL,
                        policy_id TEXT,
                        evaluated_at TEXT NOT NULL,
                        expires_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS events (
                        seq BIGSERIAL PRIMARY KEY,
                        event_id TEXT NOT NULL,
                        source_service TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        correlation_id TEXT,
                        payload_json TEXT NOT NULL,
                        event_timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS idempotency_keys (
                        idem_key TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                cur.execute("SELECT COUNT(*) FROM policies")
                if cur.fetchone()[0] == 0:
                    for p in default_policies().values():
                        cur.execute(
                            """
                            INSERT INTO policies (policy_id, name, effect, status, description,
                                time_window_json, allowed_gates_json, conditions_json, active)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (policy_id) DO NOTHING
                            """,
                            (
                                p["policyId"],
                                p["name"],
                                p["effect"],
                                p["status"],
                                p.get("description"),
                                json.dumps(p["timeWindow"]),
                                json.dumps(p["allowedGates"]),
                                json.dumps(p["conditions"]),
                                p["active"],
                            ),
                        )

                cur.execute("SELECT COUNT(*) FROM alerts")
                if cur.fetchone()[0] == 0:
                    for a in default_alerts().values():
                        self._insert_alert_row(cur, a)

                cur.execute("SELECT COUNT(*) FROM decisions")
                if cur.fetchone()[0] == 0:
                    for d in default_decisions().values():
                        self._insert_decision_row(cur, d)

                cur.execute("SELECT COUNT(*) FROM events")
                if cur.fetchone()[0] == 0:
                    for ev in default_events():
                        self._insert_event_row(cur, ev)
            conn.commit()

    @staticmethod
    def _row_to_alert(row: tuple[Any, ...]) -> Dict[str, Any]:
        return {
            "id": row[0],
            "sourceService": row[1],
            "alertType": row[2],
            "severity": row[3],
            "message": row[4],
            "relatedEventId": row[5],
            "status": row[6],
            "createdAt": row[7],
            "resolvedAt": row[8],
        }

    @staticmethod
    def _insert_alert_row(cur, a: Dict[str, Any]) -> None:
        cur.execute(
            """
            INSERT INTO alerts (id, source_service, alert_type, severity, message,
                                related_event_id, status, created_at, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                a["id"],
                a["sourceService"],
                a["alertType"],
                a["severity"],
                a["message"],
                a.get("relatedEventId"),
                a["status"],
                a["createdAt"],
                a.get("resolvedAt"),
            ),
        )

    @staticmethod
    def _row_to_decision(row: tuple[Any, ...]) -> Dict[str, Any]:
        return {
            "decisionId": row[0],
            "cardId": row[1],
            "gateId": row[2],
            "direction": row[3],
            "result": row[4],
            "reasonCode": row[5],
            "policyId": row[6],
            "evaluatedAt": row[7],
            "expiresAt": row[8],
        }

    @staticmethod
    def _insert_decision_row(cur, d: Dict[str, Any]) -> None:
        cur.execute(
            """
            INSERT INTO decisions (decision_id, card_id, gate_id, direction, result,
                                   reason_code, policy_id, evaluated_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO NOTHING
            """,
            (
                d["decisionId"],
                d["cardId"],
                d["gateId"],
                d.get("direction", "IN"),
                d["result"],
                d["reasonCode"],
                d.get("policyId"),
                d["evaluatedAt"],
                d.get("expiresAt"),
            ),
        )

    @staticmethod
    def _insert_event_row(cur, ev: Dict[str, Any]) -> None:
        cur.execute(
            """
            INSERT INTO events (event_id, source_service, event_type, correlation_id,
                                payload_json, event_timestamp, received_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                ev["eventId"],
                ev["sourceService"],
                ev["eventType"],
                ev.get("correlationId"),
                json.dumps(ev.get("payload") or {}),
                ev.get("timestamp") or ev["receivedAt"],
                ev["receivedAt"],
            ),
        )

    def list_alerts(self, limit: int) -> tuple[List[Dict[str, Any]], int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM alerts")
                total = cur.fetchone()[0]
                cur.execute(
                    """
                    SELECT id, source_service, alert_type, severity, message,
                           related_event_id, status, created_at, resolved_at
                    FROM alerts
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [self._row_to_alert(r) for r in cur.fetchall()], total

    def get_recent_alerts(self, limit: int) -> List[Dict[str, Any]]:
        items, _ = self.list_alerts(limit)
        return items

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source_service, alert_type, severity, message,
                           related_event_id, status, created_at, resolved_at
                    FROM alerts WHERE id = %s
                    """,
                    (alert_id,),
                )
                row = cur.fetchone()
                return self._row_to_alert(row) if row else None

    def create_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._insert_alert_row(cur, alert)
            conn.commit()
        return alert

    def resolve_alert(self, alert_id: str, resolved_at: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE alerts
                    SET status = 'RESOLVED', resolved_at = %s
                    WHERE id = %s
                    RETURNING id, source_service, alert_type, severity, message,
                              related_event_id, status, created_at, resolved_at
                    """,
                    (resolved_at, alert_id),
                )
                row = cur.fetchone()
            conn.commit()
            return self._row_to_alert(row) if row else None

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT policy_id, name, effect, status, description,
                           time_window_json, allowed_gates_json, conditions_json, active
                    FROM policies WHERE policy_id = %s
                    """,
                    (policy_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "policyId": row[0],
                    "name": row[1],
                    "effect": row[2],
                    "status": row[3],
                    "description": row[4],
                    "timeWindow": json.loads(row[5]),
                    "allowedGates": json.loads(row[6]),
                    "conditions": json.loads(row[7]),
                    "active": row[8],
                }

    def list_decisions(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT decision_id, card_id, gate_id, direction, result,
                           reason_code, policy_id, evaluated_at, expires_at
                    FROM decisions
                    ORDER BY evaluated_at DESC
                    LIMIT 100
                    """
                )
                return [self._row_to_decision(r) for r in cur.fetchall()]

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT decision_id, card_id, gate_id, direction, result,
                           reason_code, policy_id, evaluated_at, expires_at
                    FROM decisions WHERE decision_id = %s
                    """,
                    (decision_id,),
                )
                row = cur.fetchone()
                return self._row_to_decision(row) if row else None

    def create_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._insert_decision_row(cur, decision)
            conn.commit()
        return decision

    def count_recent_decisions_for_card(self, card_id: str, window_seconds: int = 60) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM decisions
                    WHERE card_id = %s AND evaluated_at >= %s
                    """,
                    (card_id, cutoff),
                )
                return int(cur.fetchone()[0])

    def has_idempotency_key(self, key: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM idempotency_keys WHERE idem_key = %s", (key,))
                return cur.fetchone() is not None

    def save_idempotency_key(self, key: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO idempotency_keys (idem_key, created_at)
                    VALUES (%s, %s)
                    ON CONFLICT (idem_key) DO NOTHING
                    """,
                    (key, _now_iso()),
                )
            conn.commit()

    def list_events(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT event_id, source_service, event_type, correlation_id,
                           payload_json, event_timestamp, received_at
                    FROM events
                    ORDER BY seq DESC
                    LIMIT 100
                    """
                )
                return [
                    {
                        "eventId": r[0],
                        "sourceService": r[1],
                        "eventType": r[2],
                        "correlationId": r[3],
                        "payload": json.loads(r[4]),
                        "timestamp": r[5],
                        "receivedAt": r[6],
                    }
                    for r in cur.fetchall()
                ]

    def create_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._insert_event_row(cur, event)
            conn.commit()
        return event

    def clear_data(self) -> None:
        now = _now_iso()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE events, alerts, decisions, idempotency_keys RESTART IDENTITY")
                self._insert_alert_row(
                    cur,
                    {
                        "id": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
                        "sourceService": "core-business",
                        "alertType": "SYSTEM_READY",
                        "severity": "LOW",
                        "message": "Hệ thống sẵn sàng tiếp nhận dữ liệu thật từ các nhóm mạng LAN",
                        "relatedEventId": None,
                        "status": "OPEN",
                        "createdAt": now,
                        "resolvedAt": None,
                    },
                )
                self._insert_decision_row(
                    cur,
                    {
                        "decisionId": "0196fb3d-4ad7-7d1e-9f49-bbb148d2b002",
                        "cardId": "RFID-2026-001",
                        "gateId": "GATE-01",
                        "direction": "IN",
                        "result": "ALLOW",
                        "reasonCode": "VALID_CARD",
                        "policyId": "POL-001",
                        "evaluatedAt": now,
                        "expiresAt": None,
                    },
                )
            conn.commit()

    def health_check(self) -> Dict[str, Any]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return {"backend": self.backend_name, "status": "ok"}
        except Exception as exc:
            return {"backend": self.backend_name, "status": "error", "error": str(exc)}


# ================================================================
# CHỌN KIỂU LƯU TRỮ (Dual Storage: PostgreSQL & In-Memory)
# - Mặc định dùng biến môi trường STORAGE_BACKEND (hoặc theo DATABASE_URL).
# - Có thể mở comment 1 trong 2 dòng dưới đây để ép nhanh kiểu lưu trữ.
# ================================================================
def create_store() -> BaseStore:
    """Khởi tạo Store theo STORAGE_BACKEND (postgres hoặc memory)."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    backend = os.getenv("STORAGE_BACKEND", "").strip().lower()
    if not backend:
        backend = "postgres" if database_url else "memory"

    # --- Tùy chọn ép kiểu trực tiếp (bỏ comment 1 dòng nếu muốn cố định) ---
    # backend = "postgres"  # Lưu bền vững bằng PostgreSQL (smartcampus-core-db)
    # backend = "memory"    # Lưu tạm trên RAM (In-Memory Python dict/list)

    if backend == "postgres":
        if not database_url:
            print("[STORAGE] STORAGE_BACKEND=postgres nhưng thiếu DATABASE_URL -> fallback sang InMemoryStore.")
            return InMemoryStore()
        try:
            return PostgresStore(database_url)
        except Exception as exc:
            if os.getenv("STORAGE_FALLBACK_MEMORY", "false").lower() == "true":
                print(f"[STORAGE] Không kết nối được PostgreSQL ({exc}) -> fallback sang InMemoryStore.")
                return InMemoryStore()
            raise

    return InMemoryStore()
