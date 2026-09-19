import sys
import os

# Add the parent directory to sys.path so we can import shared
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared import grounding, models, money

def verify():
    # Adding a couple of dummy checks so passed_count is 2
    from shared.models import CheckResult
    checks = [
        CheckResult(id="1", name="amount_within_cap", engine="cedar", passed=True, detail="Amount ₹100.00 <= cap ₹100.00"),
        CheckResult(id="2", name="merchant_matches", engine="cedar", passed=True, detail="merchant matches"),
        CheckResult(id="3", name="order_fulfilled", engine="python", passed=False, detail="not fulfilled")
    ]
    
    dispute = models.Dispute(
        dispute_id="dsp_test",
        mandate_id="mnd_test",
        merchant_slug="swiggy",
        amount_paise=10000, # Rs. 100.00
        txn_ts=1000,
        actions=[],
        fulfilment=models.Fulfilment("ord_1", True, 1000, 10000),
        status="contest",
        checks=checks
    )

    print("--- Testing poisoned narrative 1 (IP address and Device Fingerprint) ---")
    nar1 = "The user initiated the transaction from IP address 192.168.1.1 using device fingerprint 550e8400-e29b-41d4-a716-446655440000. 2 checks passed."
    ok1, reasons1 = grounding.check_grounding(nar1, dispute)
    print(f"Grounded: {ok1}, Reasons: {reasons1}")

    print("\n--- Testing poisoned narrative 2 (Invented Rupee Amount) ---")
    nar2 = "Although the dispute amount is Rs. 100.00, the user actually claimed a total loss of Rs. 4,500.00 which cannot be accepted. 2 checks passed."
    ok2, reasons2 = grounding.check_grounding(nar2, dispute)
    print(f"Grounded: {ok2}, Reasons: {reasons2}")
    
    print("\n--- Testing clean narrative ---")
    nar3 = "The purchase was for Rs. 100.00. Based on the rules, exactly 2 checks passed successfully."
    ok3, reasons3 = grounding.check_grounding(nar3, dispute)
    assert ok3 is True, f"Expected True, got {ok3} ({reasons3})"
    assert len(reasons3) == 0, f"Expected empty list, got {reasons3}"
    print(f"Grounded: {ok3}, Reasons: {reasons3}")

    print("\n--- Testing wrong check-count narrative ---")
    nar4 = "The purchase was for Rs. 100.00. Based on the rules, exactly 5 checks passed successfully."
    ok4, reasons4 = grounding.check_grounding(nar4, dispute)
    assert ok4 is False
    print(f"Grounded: {ok4}, Reasons: {reasons4}")

    print("\n--- Testing empty string narrative ---")
    nar5 = ""
    ok5, reasons5 = grounding.check_grounding(nar5, dispute)
    assert ok5 is False
    print(f"Grounded: {ok5}, Reasons: {reasons5}")

    print("\n--- Testing under 40 char narrative ---")
    nar6 = "This is too short. 2 checks passed."
    ok6, reasons6 = grounding.check_grounding(nar6, dispute)
    assert ok6 is False
    print(f"Grounded: {ok6}, Reasons: {reasons6}")

    print("\n--- Testing mid-sentence truncation ---")
    nar7 = "The purchase was for Rs. 100.00 and the merchant was confirmed to be"
    ok7, reasons7 = grounding.check_grounding(nar7, dispute)
    assert ok7 is False
    assert any("mid-sentence" in r for r in reasons7), f"Expected mid-sentence violation, got {reasons7}"
    print(f"Grounded: {ok7}, Reasons: {reasons7}")

if __name__ == "__main__":
    verify()
