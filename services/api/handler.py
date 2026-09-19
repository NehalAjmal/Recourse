from __future__ import annotations

import json
from typing import Any

from shared import db
from shared import audit as audit_mod


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Read-only endpoints for the dashboard. Never writes."""
    route_key = event.get("routeKey", "")

    if route_key == "GET /disputes":
        return _list_disputes(event)
    if route_key.startswith("GET /disputes/") and route_key.endswith("/audit"):
        return _get_audit(event.get("rawPath", ""))
    if route_key.startswith("GET /disputes/"):
        return _get_dispute(event.get("rawPath", ""))
    if route_key == "GET /metrics":
        return _get_metrics()

    return _response(404, {"error": "not found"})


def _list_disputes(event: dict[str, Any]) -> dict[str, Any]:
    params = event.get("queryStringParameters") or {}
    limit = min(int(params.get("limit", "25")), 100)
    cursor = params.get("cursor")

    disputes, next_cursor = db.query_disputes(limit=limit, cursor=cursor)
    items = [_dispute_to_dict(d) for d in disputes]
    body: dict[str, Any] = {"items": items}
    if next_cursor:
        body["next_cursor"] = next_cursor
    return _response(200, body)


def _get_dispute(path: str) -> dict[str, Any]:
    dispute_id = path.split("/disputes/")[1].split("/")[0]
    dispute = db.get_dispute(dispute_id)
    if dispute is None:
        return _response(404, {"error": "dispute not found"})
    return _response(200, _dispute_to_dict(dispute))


def _get_audit(path: str) -> dict[str, Any]:
    dispute_id = path.split("/disputes/")[1].split("/")[0]
    entries = audit_mod.get_audit_entries(dispute_id)
    return _response(
        200,
        {
            "entries": [
                {
                    "ts": e.ts,
                    "actor": e.actor,
                    "event": e.event,
                    "from_status": e.from_status,
                    "to_status": e.to_status,
                    "detail": e.detail,
                }
                for e in entries
            ]
        },
    )


def _get_metrics() -> dict[str, Any]:
    from eval import score
    
    def get_status(dispute_id: str) -> str:
        d = db.get_dispute(dispute_id)
        return d.status if d else "unknown"
        
    metrics = score.compute_metrics(get_status)
    return _response(200, metrics)


def _dispute_to_dict(d: Any) -> dict[str, Any]:
    mandate = db.get_mandate(d.mandate_id)
    return {
        "dispute_id": d.dispute_id,
        "mandate_id": d.mandate_id,
        "mandate": {
            "merchant_slug": mandate.merchant_slug,
            "spend_cap_paise": mandate.spend_cap_paise,
            "valid_from": mandate.valid_from,
            "valid_until": mandate.valid_until,
            "status": mandate.status,
        } if mandate else None,
        "merchant_slug": d.merchant_slug,
        "amount_paise": d.amount_paise,
        "txn_ts": d.txn_ts,
        "actions": [
            {
                "seq": a.seq,
                "action": a.action,
                "ts": a.ts,
                "payload": a.payload,
            }
            for a in d.actions
        ],
        "fulfilment": {
            "order_id": d.fulfilment.order_id,
            "delivered": d.fulfilment.delivered,
            "delivered_ts": d.fulfilment.delivered_ts,
            "amount_paise": d.fulfilment.amount_paise,
        },
        "status": d.status,
        "checks": [
            {
                "id": c.id,
                "name": c.name,
                "engine": c.engine,
                "passed": c.passed,
                "detail": c.detail,
            }
            for c in d.checks
        ],
        "confidence": d.confidence,
        "narrative": d.narrative,
        "grounded": d.grounded,
        "escalation_reason": d.escalation_reason,
    }


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body, default=str),
    }
