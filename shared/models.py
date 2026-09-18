from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Mandate:
    mandate_id: str
    user_id: str
    agent_id: str
    merchant_slug: str
    spend_cap_paise: int
    valid_from: int
    valid_until: int
    status: str  # active | revoked | expired


@dataclass
class AgentAction:
    seq: int
    action: str  # search | select | confirm | pay
    ts: int
    payload: dict[str, object]


@dataclass
class Fulfilment:
    order_id: str
    delivered: bool
    delivered_ts: int | None
    amount_paise: int


@dataclass
class CheckResult:
    id: int
    name: str
    engine: str  # cedar | python
    passed: bool
    detail: str


@dataclass
class Dispute:
    dispute_id: str
    mandate_id: str
    merchant_slug: str
    amount_paise: int
    txn_ts: int
    actions: list[AgentAction]
    fulfilment: Fulfilment
    status: str  # received | contest | escalate | accept
    checks: list[CheckResult] = field(default_factory=list)
    confidence: float = 0.0
    narrative: str | None = None
    grounded: bool = False
    escalation_reason: str | None = None


@dataclass
class AuditEntry:
    ts: int
    actor: str  # system:ingest | system:evaluate | system:narrate | avp:cedar
    event: str
    from_status: str
    to_status: str
    detail: str = ""
