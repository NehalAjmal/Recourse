from __future__ import annotations

import re


def paise_to_rupees(paise: int) -> str:
    """Format integer paise as a display string: 124900 -> '1,249.00'."""
    rupees = paise // 100
    remaining_paise = paise % 100
    rupee_str = f"{rupees:,}"
    return f"{rupee_str}.{remaining_paise:02d}"


def format_inr(paise: int) -> str:
    """Format integer paise with the rupee symbol: 124900 -> '\u20b91,249.00'."""
    return f"\u20b9{paise_to_rupees(paise)}"


def parse_rupee_amount(text: str) -> int | None:
    """Extract a rupee amount from free text and return it as integer paise.

    Handles formats like '\u20b91,249.00', 'Rs. 1249', 'INR 1,249.50'.
    Returns None if no amount is found.
    """
    pattern = r"(?:\u20b9|Rs\.?\s*|INR\s*)\s*([\d,]+(?:\.\d{1,2})?)"
    match = re.search(pattern, text)
    if match is None:
        return None
    raw = match.group(1).replace(",", "")
    if "." in raw:
        parts = raw.split(".")
        rupees = int(parts[0])
        paise_str = parts[1].ljust(2, "0")[:2]
        return rupees * 100 + int(paise_str)
    return int(raw) * 100
