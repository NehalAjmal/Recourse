from __future__ import annotations

import json
import os
from typing import Any

import boto3

from shared import audit, checks, db

avp_client = boto3.client("verifiedpermissions")
lambda_client = boto3.client("lambda")

POLICY_STORE_ID = os.environ.get("POLICY_STORE_ID", "")
NARRATE_FUNCTION_NAME = os.environ.get("NARRATE_FUNCTION_NAME", "")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run Cedar + Python checks, decide contest/escalate/accept."""
    dispute_id = event.get("dispute_id")
    if not dispute_id:
        return {"statusCode": 400, "body": "dispute_id missing"}

    dispute = db.get_dispute(dispute_id)
    if not dispute:
        return {"statusCode": 404, "body": "dispute not found"}

    mandate = db.get_mandate(dispute.mandate_id)
    if not mandate:
        return {"statusCode": 404, "body": "mandate not found"}

    # 1. Run Cedar checks
    avp_resp = avp_client.is_authorized(
        policyStoreId=POLICY_STORE_ID,
        principal={
            "entityType": "Recourse::Mandate",
            "entityId": mandate.mandate_id,
        },
        action={
            "actionType": "Recourse::Action",
            "actionId": "purchase",
        },
        resource={
            "entityType": "Recourse::Transaction",
            "entityId": "txn",
        },
        entities={
            "entityList": [
                {
                    "identifier": {
                        "entityType": "Recourse::Mandate",
                        "entityId": mandate.mandate_id,
                    },
                    "attributes": {
                        "spend_cap_paise": {"long": mandate.spend_cap_paise},
                        "merchant_slug": {"string": mandate.merchant_slug},
                        "status": {"string": mandate.status},
                        "valid_from": {"long": mandate.valid_from},
                        "valid_until": {"long": mandate.valid_until},
                    },
                },
                {
                    "identifier": {
                        "entityType": "Recourse::Transaction",
                        "entityId": "txn",
                    },
                    "attributes": {
                        "amount_paise": {"long": dispute.amount_paise},
                        "merchant_slug": {"string": dispute.merchant_slug},
                        "txn_ts": {"long": dispute.txn_ts},
                    },
                },
            ]
        },
    )

    cedar_decision = avp_resp.get("decision")
    print(f"Cedar decision: {cedar_decision}, determiningPolicies: {avp_resp.get('determiningPolicies')}")

    # Python explanations for checks 1-3
    c1 = checks.check_amount_within_cap(dispute, mandate)
    c1.engine = "cedar"
    c2 = checks.check_merchant_matches(dispute, mandate)
    c2.engine = "cedar"
    c3 = checks.check_mandate_active(dispute, mandate)
    c3.engine = "cedar"

    # 2. Run Python checks
    c4 = checks.check_order_fulfilled(dispute, mandate)
    c5 = checks.check_timeline_consistent(dispute, mandate)
    c6 = checks.check_no_unexplained_duplicate(dispute, mandate)

    all_checks = [c1, c2, c3, c4, c5, c6]
    passed_count = sum(1 for c in all_checks if c.passed)
    confidence = passed_count / 6.0

    if passed_count == 6:
        status = "contest"
        escalation_reason = None
    elif passed_count >= 4:
        status = "escalate"
        failed = [c.name for c in all_checks if not c.passed]
        escalation_reason = f"Failed checks: {', '.join(failed)}"
    else:
        status = "accept"
        escalation_reason = None

    # Update DB
    db.update_dispute_status(
        dispute_id=dispute.dispute_id,
        status=status,
        checks=all_checks,
        confidence=confidence,
        escalation_reason=escalation_reason,
    )

    # Audit log
    audit.append_audit_entry(
        dispute_id=dispute.dispute_id,
        actor="system:evaluate",
        event="checks_completed",
        from_status="received",
        to_status=status,
        detail=f"Confidence {confidence:.2f} ({passed_count}/6 passed)",
    )

    # Trigger narrate if contest
    if status == "contest" and NARRATE_FUNCTION_NAME:
        lambda_client.invoke(
            FunctionName=NARRATE_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps({"dispute_id": dispute.dispute_id}),
        )

    return {"statusCode": 200, "body": json.dumps({"status": status})}
