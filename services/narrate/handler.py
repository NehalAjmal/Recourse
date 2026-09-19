from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from shared import audit, db, grounding

_LLM_API_KEY = None

def _get_api_key() -> str:
    global _LLM_API_KEY
    if _LLM_API_KEY is not None:
        return _LLM_API_KEY
    
    ssm = boto3.client("ssm")
    param_name = os.environ.get("LLM_API_KEY_SSM_PARAM")
    if not param_name:
        raise ValueError("LLM_API_KEY_SSM_PARAM env var not set")
        
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    _LLM_API_KEY = response["Parameter"]["Value"]
    return _LLM_API_KEY

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """One Gemini API call + grounding check. Never invoked except by evaluate."""
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
        api_key = _get_api_key()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps({
                "model": "openai/gpt-oss-20b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "recourse-hackathon/1.0"
            },
            method="POST",
        )
        # 20 second timeout for API
        with urllib.request.urlopen(req, timeout=20.0) as response:
            resp_body = json.loads(response.read().decode("utf-8"))
            narrative = resp_body["choices"][0]["message"]["content"]
            
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        _fail_and_escalate(dispute.dispute_id, f"Groq API error {e.code}: {err_msg}")
        return {"statusCode": 200, "body": "escalated due to generation failure"}
    except (BotoCoreError, ClientError, KeyError, ValueError, urllib.error.URLError, json.JSONDecodeError, IndexError) as e:
        _fail_and_escalate(dispute.dispute_id, f"Groq generation failed: {e}")
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
