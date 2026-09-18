from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shared.audit import append_audit_entry, get_audit_entries
from shared.models import AuditEntry


@pytest.fixture(autouse=True)
def _mock_dynamodb():
    """Replace the DynamoDB table with a mock for all audit tests."""
    with patch("shared.audit._table") as mock_table:
        mock_table.put_item = MagicMock()
        mock_table.query = MagicMock(return_value={"Items": []})
        yield mock_table


def test_append_audit_entry_writes_correct_shape(_mock_dynamodb):
    entry = append_audit_entry(
        dispute_id="dsp_test123",
        actor="system:ingest",
        event="dispute_created",
        from_status="",
        to_status="received",
        detail="initial ingestion",
    )

    assert isinstance(entry, AuditEntry)
    assert entry.actor == "system:ingest"
    assert entry.event == "dispute_created"
    assert entry.from_status == ""
    assert entry.to_status == "received"
    assert entry.detail == "initial ingestion"
    assert entry.ts > 0

    _mock_dynamodb.put_item.assert_called_once()
    call_kwargs = _mock_dynamodb.put_item.call_args
    item = call_kwargs.kwargs["Item"] if "Item" in call_kwargs.kwargs else call_kwargs[1]["Item"]
    assert item["PK"] == "DISPUTE#dsp_test123"
    assert item["SK"].startswith("AUDIT#")
    assert item["actor"] == "system:ingest"
    assert item["event"] == "dispute_created"


def test_append_audit_entry_uses_condition_expression(_mock_dynamodb):
    append_audit_entry(
        dispute_id="dsp_test456",
        actor="system:evaluate",
        event="checks_completed",
        from_status="received",
        to_status="contest",
    )

    call_kwargs = _mock_dynamodb.put_item.call_args
    condition = (
        call_kwargs.kwargs.get("ConditionExpression")
        if call_kwargs.kwargs
        else None
    )
    assert condition is not None, "audit writes must use a condition expression to prevent overwrites"


def test_get_audit_entries_returns_typed_list(_mock_dynamodb):
    _mock_dynamodb.query.return_value = {
        "Items": [
            {
                "ts": 1726600000,
                "actor": "system:evaluate",
                "event": "checks_completed",
                "from_status": "received",
                "to_status": "contest",
                "detail": "",
            },
            {
                "ts": 1726599900,
                "actor": "system:ingest",
                "event": "dispute_created",
                "from_status": "",
                "to_status": "received",
                "detail": "initial",
            },
        ]
    }

    entries = get_audit_entries("dsp_test789")

    assert len(entries) == 2
    assert all(isinstance(e, AuditEntry) for e in entries)
    assert entries[0].ts == 1726600000
    assert entries[1].actor == "system:ingest"


def test_get_audit_entries_queries_reverse_chronological(_mock_dynamodb):
    get_audit_entries("dsp_test000")

    call_kwargs = _mock_dynamodb.query.call_args
    assert call_kwargs.kwargs.get("ScanIndexForward") is False, (
        "audit entries should be returned reverse-chronologically"
    )
