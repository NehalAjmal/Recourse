from __future__ import annotations

import time
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr

from shared.models import AuditEntry

import os

_table_name = os.environ.get("TABLE_NAME", "Recourse")
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_table_name)

_SEQ_COUNTER: int = 0


def _next_seq() -> int:
    global _SEQ_COUNTER
    _SEQ_COUNTER += 1
    return _SEQ_COUNTER


def append_audit_entry(
    dispute_id: str,
    actor: str,
    event: str,
    from_status: str,
    to_status: str,
    detail: str = "",
) -> AuditEntry:
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = int(now.timestamp())
    seq = _next_seq()
    iso_ts = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    sk = f"AUDIT#{iso_ts}#{seq:04d}"

    entry = AuditEntry(
        ts=ts,
        actor=actor,
        event=event,
        from_status=from_status,
        to_status=to_status,
        detail=detail,
    )

    _table.put_item(
        Item={
            "PK": f"DISPUTE#{dispute_id}",
            "SK": sk,
            "ts": ts,
            "actor": actor,
            "event": event,
            "from_status": from_status,
            "to_status": to_status,
            "detail": detail,
        },
        ConditionExpression=Attr("SK").not_exists(),
    )

    return entry


def get_audit_entries(dispute_id: str) -> list[AuditEntry]:
    from boto3.dynamodb.conditions import Key

    resp = _table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"DISPUTE#{dispute_id}")
            & Key("SK").begins_with("AUDIT#")
        ),
        ScanIndexForward=False,
    )
    return [
        AuditEntry(
            ts=int(item["ts"]),
            actor=item["actor"],
            event=item["event"],
            from_status=item["from_status"],
            to_status=item["to_status"],
            detail=item.get("detail", ""),
        )
        for item in resp.get("Items", [])
    ]
