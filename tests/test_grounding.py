import ast
import os
from shared import grounding
from shared.models import Dispute, Fulfilment

def test_grounding_no_network_imports():
    """Assert that the grounding check imports no network-capable modules."""
    filepath = os.path.join(os.path.dirname(__file__), "..", "shared", "grounding.py")
    with open(filepath, "r") as f:
        tree = ast.parse(f.read())
        
    banned_modules = {"requests", "urllib", "http", "boto3", "socket", "urllib3", "httpx"}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split('.')[0]
                assert base_module not in banned_modules, f"Grounding module illegally imported {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                assert base_module not in banned_modules, f"Grounding module illegally imported {node.module}"


def test_grounding_rejects_ip():
    dispute = Dispute(
        dispute_id="dsp_1",
        mandate_id="mnd_1",
        merchant_slug="swiggy",
        amount_paise=10000,
        txn_ts=1000,
        actions=[],
        fulfilment=Fulfilment("ord_1", True, 1000, 10000),
        status="contest"
    )
    is_grounded, reasons = grounding.check_grounding("The user logged in from 192.168.1.1 and placed the order.", dispute)
    assert not is_grounded
    assert any("IP address" in r for r in reasons)

def test_grounding_rejects_fingerprint():
    dispute = Dispute(
        dispute_id="dsp_1",
        mandate_id="mnd_1",
        merchant_slug="swiggy",
        amount_paise=10000,
        txn_ts=1000,
        actions=[],
        fulfilment=Fulfilment("ord_1", True, 1000, 10000),
        status="contest"
    )
    is_grounded, reasons = grounding.check_grounding("Device fingerprint 123e4567-e89b-12d3-a456-426614174000 was used.", dispute)
    assert not is_grounded
    assert any("fingerprint or UUID" in r for r in reasons)

def test_grounding_rejects_invented_rupee():
    dispute = Dispute(
        dispute_id="dsp_1",
        mandate_id="mnd_1",
        merchant_slug="swiggy",
        amount_paise=10000, # 100.00
        txn_ts=1000,
        actions=[],
        fulfilment=Fulfilment("ord_1", True, 1000, 10000),
        status="contest"
    )
    is_grounded, reasons = grounding.check_grounding("The user spent ₹100.00, but actually it was Rs. 150.00.", dispute)
    assert not is_grounded
    assert any("invented rupee amount" in r for r in reasons)

def test_grounding_accepts_valid():
    dispute = Dispute(
        dispute_id="dsp_1",
        mandate_id="mnd_1",
        merchant_slug="swiggy",
        amount_paise=10000, # 100.00
        txn_ts=1000,
        actions=[],
        fulfilment=Fulfilment("ord_1", True, 1000, 10000),
        status="contest"
    )
    is_grounded, reasons = grounding.check_grounding("The transaction was for ₹100.00. The order was delivered.", dispute)
    assert is_grounded
    assert len(reasons) == 0

def test_grounding_rejects_mid_sentence():
    dispute = Dispute(
        dispute_id="dsp_1",
        mandate_id="mnd_1",
        merchant_slug="swiggy",
        amount_paise=10000,
        txn_ts=1000,
        actions=[],
        fulfilment=Fulfilment("ord_1", True, 1000, 10000),
        status="contest"
    )
    is_grounded, reasons = grounding.check_grounding("The transaction was for ₹100.00 and it was delivered to the", dispute)
    assert not is_grounded
    assert any("mid-sentence" in r for r in reasons)
