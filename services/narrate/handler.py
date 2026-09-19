from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from shared import audit, db, grounding

# 20 second timeout for Bedrock
bedrock_config = Config(read_timeout=20, retries={'max_attempts': 0})
bedrock_client = boto3.client("bedrock-runtime", config=bedrock_config)

# Using Haiku for fast, cheap inference
MODEL_ID = "us.anthropic.claude-3-haiku-20240307-v1:0"


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """One Bedrock call + grounding check. Never invoked except by evaluate."""
    dispute_id = event.get("dispute_id")
    if not dispute_id:
        return {"statusCode": 400, "body": "dispute_id missing"}

    dispute = db.get_dispute(dispute_id)
    if not dispute:
        return {"statusCode": 404, "body": "dispute not found"}

    mandate = db.get_mandate(dispute.mandate_id)
    if not mandate:
        return {"statusCode": 404, "body": "mandate not found"}

    prompt = (
        f"Write a short, factual 2-sentence summary of the following transaction dispute.\n"
        f"Do not make any judgements, decisions, or recommendations.\n"
        f"Mandate cap: {mandate.spend_cap_paise} paise\n"
        f"Merchant: {dispute.merchant_slug}\n"
        f"Transaction amount: {dispute.amount_paise} paise\n"
        f"Delivered: {'Yes' if dispute.fulfilment.delivered else 'No'}\n"
        f"Action log: {', '.join(a.action for a in dispute.actions)}\n"
    )

    try:
        response = bedrock_client.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.0}
        )
        narrative = response['output']['message']['content'][0]['text']
    except (BotoCoreError, ClientError, KeyError) as e:
        _fail_and_escalate(dispute.dispute_id, f"Bedrock generation failed: {e}")
        return {"statusCode": 200, "body": "escalated due to generation failure"}

    is_grounded, failure_reasons = grounding.check_grounding(narrative, dispute)

    if not is_grounded:
        reason = "; ".join(failure_reasons)
        _fail_and_escalate(dispute.dispute_id, reason)
        return {"statusCode": 200, "body": "escalated due to grounding failure"}

    # Success path
    db.update_dispute_status(
        dispute_id=dispute.dispute_id,
        status="contest", # It stays contest
        narrative=narrative,
        grounded=True
    )
    
    audit.append_audit_entry(
        dispute_id=dispute.dispute_id,
        actor="system:narrate",
        event="narrative_generated",
        from_status="contest",
        to_status="contest",
        detail="Narrative generated and grounded successfully",
    )

    return {"statusCode": 200, "body": "narrative generated successfully"}


def _fail_and_escalate(dispute_id: str, reason: str) -> None:
    db.update_dispute_status(
        dispute_id=dispute_id,
        status="escalate",
        escalation_reason=reason,
        narrative=None, # Discard narrative explicitly
        grounded=False
    )
    audit.append_audit_entry(
        dispute_id=dispute_id,
        actor="system:narrate",
        event="narrative_failed",
        from_status="contest",
        to_status="escalate",
        detail=reason,
    )
