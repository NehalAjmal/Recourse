from __future__ import annotations
import ast
import os
import re

from shared import money
from shared.models import Dispute

def check_grounding(narrative: str, dispute: Dispute) -> tuple[bool, list[str]]:
    """
    Deterministically check the narrative against the dispute's structured data.
    Pure function, no network calls.
    Returns (is_grounded, list of failure reasons)
    """
    violations = []
    
    # 0. Length check
    if not narrative or len(narrative) < 40:
        violations.append("Narrative is empty or under 40 characters")
        
    # 1. Check for IP addresses
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    if re.search(ip_pattern, narrative):
        violations.append("Narrative contains an IP address")
        
    # 2. Check for device fingerprints (UUIDs or long hex)
    uuid_pattern = r'\b[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}\b'
    hex_pattern = r'\b[0-9a-fA-F]{32,}\b'
    if re.search(uuid_pattern, narrative) or re.search(hex_pattern, narrative):
        violations.append("Narrative contains a device fingerprint or UUID")
        
    # 3. Check for invented rupee amounts
    amount_pattern = r"(?:\u20b9|Rs\.?\s*|INR\s*)\s*([\d,]+(?:\.\d{1,2})?)"
    matches = re.finditer(amount_pattern, narrative)
    allowed_amounts = {dispute.amount_paise, dispute.fulfilment.amount_paise}
    for match in matches:
        amt_str = match.group(0)
        paise = money.parse_rupee_amount(amt_str)
        if paise is not None and paise not in allowed_amounts:
            violations.append(f"Narrative contains invented rupee amount: {amt_str}")
            
    # 4. Check for URLs or external links
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, narrative):
        violations.append("Narrative contains a URL")

    # 5. Check-count verification
    # Look for patterns like "X checks passed", "X/6 passed", "passed X checks"
    passed_count = sum(1 for c in dispute.checks if c.passed) if getattr(dispute, 'checks', None) else 0
    check_count_pattern = r'\b(\d+)\s*(?:/6)?\s*(?:checks\s*)?passed\b|\bpassed\s*(\d+)\s*checks\b'
    for match in re.finditer(check_count_pattern, narrative, re.IGNORECASE):
        # One of the groups will contain the digit
        claimed_str = match.group(1) or match.group(2)
        if claimed_str and int(claimed_str) != passed_count:
            violations.append(f"Narrative claims {claimed_str} checks passed, but {passed_count} actually passed")

    # 6. Ends mid-sentence — truncated generation output
    if narrative and not narrative.rstrip().endswith(('.', '!', '?')):
        violations.append("Narrative ends mid-sentence")
        
    return len(violations) == 0, violations
