from __future__ import annotations

from shared.models import CheckResult, Dispute, Mandate
from shared import db, money


def check_amount_within_cap(dispute: Dispute, mandate: Mandate) -> CheckResult:
    passed = dispute.amount_paise <= mandate.spend_cap_paise
    detail = (
        f"amount ({money.format_inr(dispute.amount_paise)}) <= cap ({money.format_inr(mandate.spend_cap_paise)})"
        if passed
        else f"amount ({money.format_inr(dispute.amount_paise)}) > cap ({money.format_inr(mandate.spend_cap_paise)})"
    )
    return CheckResult(
        id=1,
        name="amount_within_cap",
        engine="python",
        passed=passed,
        detail=detail,
    )


def check_merchant_matches(dispute: Dispute, mandate: Mandate) -> CheckResult:
    passed = dispute.merchant_slug == mandate.merchant_slug
    detail = (
        f"merchant ({dispute.merchant_slug}) == mandate ({mandate.merchant_slug})"
        if passed
        else f"merchant ({dispute.merchant_slug}) != mandate ({mandate.merchant_slug})"
    )
    return CheckResult(
        id=2,
        name="merchant_matches",
        engine="python",
        passed=passed,
        detail=detail,
    )


def check_mandate_active(dispute: Dispute, mandate: Mandate) -> CheckResult:
    active = mandate.status == "active"
    in_window = mandate.valid_from <= dispute.txn_ts <= mandate.valid_until
    passed = active and in_window
    detail = (
        f"status {mandate.status}, txn {dispute.txn_ts} within [{mandate.valid_from}, {mandate.valid_until}]"
        if passed
        else f"status {mandate.status} or txn {dispute.txn_ts} outside [{mandate.valid_from}, {mandate.valid_until}]"
    )
    return CheckResult(
        id=3,
        name="mandate_active",
        engine="python",
        passed=passed,
        detail=detail,
    )


def check_order_fulfilled(dispute: Dispute, mandate: Mandate) -> CheckResult:
    if not dispute.fulfilment.delivered:
        return CheckResult(
            id=4,
            name="order_fulfilled",
            engine="python",
            passed=False,
            detail="order not delivered",
        )
    if dispute.fulfilment.delivered_ts is None:
        return CheckResult(
            id=4,
            name="order_fulfilled",
            engine="python",
            passed=False,
            detail="delivered but missing delivered_ts",
        )
    passed = dispute.fulfilment.delivered_ts >= dispute.txn_ts
    detail = (
        f"delivered at {dispute.fulfilment.delivered_ts} >= txn {dispute.txn_ts}"
        if passed
        else f"delivered at {dispute.fulfilment.delivered_ts} < txn {dispute.txn_ts}"
    )
    return CheckResult(
        id=4,
        name="order_fulfilled",
        engine="python",
        passed=passed,
        detail=detail,
    )


def check_timeline_consistent(dispute: Dispute, mandate: Mandate) -> CheckResult:
    actions = dispute.actions
    expected_actions = ["search", "select", "confirm", "pay"]
    if len(actions) != 4:
        return CheckResult(
            id=5,
            name="timeline_consistent",
            engine="python",
            passed=False,
            detail=f"found {len(actions)} actions, expected 4",
        )

    for i, a in enumerate(actions):
        if a.action != expected_actions[i]:
            return CheckResult(
                id=5,
                name="timeline_consistent",
                engine="python",
                passed=False,
                detail=f"action {i+1} is {a.action}, expected {expected_actions[i]}",
            )
        if i > 0 and a.ts <= actions[i - 1].ts:
            return CheckResult(
                id=5,
                name="timeline_consistent",
                engine="python",
                passed=False,
                detail=f"action {a.action} ts {a.ts} <= previous ts {actions[i-1].ts}",
            )
        if not (mandate.valid_from <= a.ts <= mandate.valid_until):
            return CheckResult(
                id=5,
                name="timeline_consistent",
                engine="python",
                passed=False,
                detail=f"action {a.action} ts {a.ts} outside mandate window [{mandate.valid_from}, {mandate.valid_until}]",
            )

    pay_action = actions[3]
    if not (dispute.txn_ts - 120 <= pay_action.ts <= dispute.txn_ts + 120):
        return CheckResult(
            id=5,
            name="timeline_consistent",
            engine="python",
            passed=False,
            detail=f"pay ts {pay_action.ts} differs from txn_ts {dispute.txn_ts} by > 120s",
        )

    return CheckResult(
        id=5,
        name="timeline_consistent",
        engine="python",
        passed=True,
        detail="sequence search->select->confirm->pay strictly increasing inside window, pay within 120s",
    )


def check_no_unexplained_duplicate(dispute: Dispute, mandate: Mandate) -> CheckResult:
    probes = db.query_duplicate_probes(
        mandate.mandate_id, dispute.txn_ts, window_seconds=300
    )
    
    # We must exclude the current order
    other_probes = [p for p in probes if p.get("order_id") != dispute.fulfilment.order_id]

    if other_probes:
        # Just grab the first one to show in detail
        other = other_probes[0]
        return CheckResult(
            id=6,
            name="no_unexplained_duplicate",
            engine="python",
            passed=False,
            detail=f"found duplicate order {other.get('order_id')} at ts {other.get('txn_ts')} within 300s window",
        )

    return CheckResult(
        id=6,
        name="no_unexplained_duplicate",
        engine="python",
        passed=True,
        detail="no other orders on this mandate within 300s window",
    )
