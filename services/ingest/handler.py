from __future__ import annotations

import json
import os
from typing import Any

import boto3

from shared import audit, db
from shared.models import AgentAction, Dispute, Fulfilment, Mandate

lambda_client = boto3.client("lambda")
EVALUATE_FUNCTION_NAME = os.environ.get("EVALUATE_FUNCTION_NAME", "")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Receive a dispute event, validate shape, write, invoke evaluate."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _error(400, "Invalid JSON body")

    try:
        mandate_data = body["mandate"]
        mandate = Mandate(
            mandate_id=mandate_data["mandate_id"],
            user_id=mandate_data["user_id"],
            agent_id=mandate_data["agent_id"],
            merchant_slug=mandate_data["merchant_slug"],
            spend_cap_paise=int(mandate_data["spend_cap_paise"]),
            valid_from=int(mandate_data["valid_from"]),
            valid_until=int(mandate_data["valid_until"]),
            status=mandate_data["status"],
        )

        actions = [
            AgentAction(
                seq=int(a["seq"]),
                action=a["action"],
                ts=int(a["ts"]),
                payload=a.get("payload", {}),
            )
            for a in body["actions"]
        ]

        fulfilment_data = body["fulfilment"]
        fulfilment = Fulfilment(
            order_id=fulfilment_data["order_id"],
            delivered=bool(fulfilment_data["delivered"]),
            delivered_ts=(
                int(fulfilment_data["delivered_ts"])
                if fulfilment_data.get("delivered_ts") is not None
                else None
            ),
            amount_paise=int(fulfilment_data["amount_paise"]),
        )

        dispute = Dispute(
            dispute_id=body["dispute_id"],
            mandate_id=mandate.mandate_id,
            merchant_slug=body["merchant_slug"],
            amount_paise=int(body["amount_paise"]),
            txn_ts=int(body["txn_ts"]),
            actions=actions,
            fulfilment=fulfilment,
            status="received",
        )
    except (KeyError, ValueError, TypeError) as e:
        return _error(400, f"Invalid payload shape: {e}")

    # Write to DB
    db.put_mandate(mandate)
    db.put_dispute(dispute)
    db.put_duplicate_probe(mandate.mandate_id, dispute.txn_ts, fulfilment.order_id)

    # Audit entry
    audit.append_audit_entry(
        dispute_id=dispute.dispute_id,
        actor="system:ingest",
        event="dispute_received",
        from_status="",
        to_status="received",
        detail="Dispute ingested via API",
    )

    # Invoke evaluate
    if EVALUATE_FUNCTION_NAME:
        lambda_client.invoke(
            FunctionName=EVALUATE_FUNCTION_NAME,
            InvocationType="Event",  # Asynchronous
            Payload=json.dumps({"dispute_id": dispute.dispute_id}),
        )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"dispute_id": dispute.dispute_id, "status": "received"}),
    }


def _error(status: int, message: str) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
