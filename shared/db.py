from __future__ import annotations

import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from shared.models import (
    AgentAction,
    AuditEntry,
    CheckResult,
    Dispute,
    Fulfilment,
    Mandate,
)

_table_name = os.environ.get("TABLE_NAME", "Recourse")
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_table_name)

QUEUE_PK = "QUEUE"


def _dispute_to_item(dispute: Dispute) -> dict[str, Any]:
    return {
        "PK": f"DISPUTE#{dispute.dispute_id}",
        "SK": "META",
        "GSI1PK": QUEUE_PK,
        "GSI1SK": f"{dispute.confidence:06.4f}#{dispute.dispute_id}",
        "dispute_id": dispute.dispute_id,
        "mandate_id": dispute.mandate_id,
        "merchant_slug": dispute.merchant_slug,
        "amount_paise": dispute.amount_paise,
        "txn_ts": dispute.txn_ts,
        "actions": [
            {
                "seq": a.seq,
                "action": a.action,
                "ts": a.ts,
                "payload": a.payload,
            }
            for a in dispute.actions
        ],
        "fulfilment": {
            "order_id": dispute.fulfilment.order_id,
            "delivered": dispute.fulfilment.delivered,
            "delivered_ts": dispute.fulfilment.delivered_ts,
            "amount_paise": dispute.fulfilment.amount_paise,
        },
        "status": dispute.status,
        "checks": [
            {
                "id": c.id,
                "name": c.name,
                "engine": c.engine,
                "passed": c.passed,
                "detail": c.detail,
            }
            for c in dispute.checks
        ],
        "confidence": str(dispute.confidence),
        "narrative": dispute.narrative,
        "grounded": dispute.grounded,
        "escalation_reason": dispute.escalation_reason,
    }


def _item_to_dispute(item: dict[str, Any]) -> Dispute:
    return Dispute(
        dispute_id=item["dispute_id"],
        mandate_id=item["mandate_id"],
        merchant_slug=item["merchant_slug"],
        amount_paise=int(item["amount_paise"]),
        txn_ts=int(item["txn_ts"]),
        actions=[
            AgentAction(
                seq=int(a["seq"]),
                action=a["action"],
                ts=int(a["ts"]),
                payload=a.get("payload", {}),
            )
            for a in item["actions"]
        ],
        fulfilment=Fulfilment(
            order_id=item["fulfilment"]["order_id"],
            delivered=item["fulfilment"]["delivered"],
            delivered_ts=(
                int(item["fulfilment"]["delivered_ts"])
                if item["fulfilment"].get("delivered_ts") is not None
                else None
            ),
            amount_paise=int(item["fulfilment"]["amount_paise"]),
        ),
        status=item["status"],
        checks=[
            CheckResult(
                id=int(c["id"]),
                name=c["name"],
                engine=c["engine"],
                passed=c["passed"],
                detail=c["detail"],
            )
            for c in item.get("checks", [])
        ],
        confidence=float(item.get("confidence", 0)),
        narrative=item.get("narrative"),
        grounded=item.get("grounded", False),
        escalation_reason=item.get("escalation_reason"),
    )


def _mandate_to_item(mandate: Mandate) -> dict[str, Any]:
    return {
        "PK": f"MANDATE#{mandate.mandate_id}",
        "SK": "META",
        "mandate_id": mandate.mandate_id,
        "user_id": mandate.user_id,
        "agent_id": mandate.agent_id,
        "merchant_slug": mandate.merchant_slug,
        "spend_cap_paise": mandate.spend_cap_paise,
        "valid_from": mandate.valid_from,
        "valid_until": mandate.valid_until,
        "status": mandate.status,
    }


def _item_to_mandate(item: dict[str, Any]) -> Mandate:
    return Mandate(
        mandate_id=item["mandate_id"],
        user_id=item["user_id"],
        agent_id=item["agent_id"],
        merchant_slug=item["merchant_slug"],
        spend_cap_paise=int(item["spend_cap_paise"]),
        valid_from=int(item["valid_from"]),
        valid_until=int(item["valid_until"]),
        status=item["status"],
    )


def put_dispute(dispute: Dispute) -> None:
    _table.put_item(Item=_dispute_to_item(dispute))


def get_dispute(dispute_id: str) -> Dispute | None:
    resp = _table.get_item(
        Key={"PK": f"DISPUTE#{dispute_id}", "SK": "META"},
    )
    item = resp.get("Item")
    if item is None:
        return None
    return _item_to_dispute(item)


def update_dispute_status(
    dispute_id: str,
    status: str,
    checks: list[CheckResult] | None = None,
    confidence: float | None = None,
    narrative: str | None = None,
    grounded: bool | None = None,
    escalation_reason: str | None = None,
) -> None:
    expressions: list[str] = ["#s = :status"]
    names: dict[str, str] = {"#s": "status"}
    values: dict[str, Any] = {":status": status}

    if checks is not None:
        expressions.append("checks = :checks")
        values[":checks"] = [
            {
                "id": c.id,
                "name": c.name,
                "engine": c.engine,
                "passed": c.passed,
                "detail": c.detail,
            }
            for c in checks
        ]

    if confidence is not None:
        expressions.append("confidence = :confidence")
        values[":confidence"] = str(confidence)
        expressions.append("GSI1SK = :gsi1sk")
        values[":gsi1sk"] = f"{confidence:06.4f}#{dispute_id}"

    if narrative is not None:
        expressions.append("narrative = :narrative")
        values[":narrative"] = narrative

    if grounded is not None:
        expressions.append("grounded = :grounded")
        values[":grounded"] = grounded

    if escalation_reason is not None:
        expressions.append("escalation_reason = :escalation_reason")
        values[":escalation_reason"] = escalation_reason

    _table.update_item(
        Key={"PK": f"DISPUTE#{dispute_id}", "SK": "META"},
        UpdateExpression="SET " + ", ".join(expressions),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def query_disputes(
    limit: int = 25,
    cursor: str | None = None,
) -> tuple[list[Dispute], str | None]:
    kwargs: dict[str, Any] = {
        "IndexName": "GSI1",
        "KeyConditionExpression": Key("GSI1PK").eq(QUEUE_PK),
        "Limit": limit,
    }
    if cursor:
        kwargs["ExclusiveStartKey"] = _decode_cursor(cursor)

    resp = _table.query(**kwargs)
    disputes = [_item_to_dispute(item) for item in resp.get("Items", [])]
    next_key = resp.get("LastEvaluatedKey")
    next_cursor = _encode_cursor(next_key) if next_key else None
    return disputes, next_cursor


def _encode_cursor(key: dict[str, Any]) -> str:
    import json
    import base64

    return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()


def _decode_cursor(cursor: str) -> dict[str, Any]:
    import json
    import base64

    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


def put_mandate(mandate: Mandate) -> None:
    _table.put_item(Item=_mandate_to_item(mandate))


def get_mandate(mandate_id: str) -> Mandate | None:
    resp = _table.get_item(
        Key={"PK": f"MANDATE#{mandate_id}", "SK": "META"},
    )
    item = resp.get("Item")
    if item is None:
        return None
    return _item_to_mandate(item)


def put_duplicate_probe(mandate_id: str, txn_ts: int, order_id: str) -> None:
    _table.put_item(
        Item={
            "PK": f"MANDATE#{mandate_id}",
            "SK": f"ORDER#{txn_ts}#{order_id}",
            "mandate_id": mandate_id,
            "txn_ts": txn_ts,
            "order_id": order_id,
        }
    )


def query_duplicate_probes(
    mandate_id: str, txn_ts: int, window_seconds: int = 300
) -> list[dict[str, Any]]:
    resp = _table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"MANDATE#{mandate_id}")
            & Key("SK").between(
                f"ORDER#{txn_ts - window_seconds}#",
                f"ORDER#{txn_ts + window_seconds}#~",
            )
        ),
    )
    return resp.get("Items", [])
