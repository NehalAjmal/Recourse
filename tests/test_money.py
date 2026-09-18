from __future__ import annotations

from shared.money import format_inr, paise_to_rupees, parse_rupee_amount


def test_paise_to_rupees_basic():
    assert paise_to_rupees(124900) == "1,249.00"


def test_paise_to_rupees_zero():
    assert paise_to_rupees(0) == "0.00"


def test_paise_to_rupees_small():
    assert paise_to_rupees(50) == "0.50"


def test_format_inr():
    assert format_inr(124900) == "\u20b91,249.00"


def test_parse_rupee_amount_symbol():
    assert parse_rupee_amount("The amount was \u20b91,249.00 total") == 124900


def test_parse_rupee_amount_rs():
    assert parse_rupee_amount("Rs. 500") == 50000


def test_parse_rupee_amount_inr():
    assert parse_rupee_amount("INR 1,249.50") == 124950


def test_parse_rupee_amount_no_match():
    assert parse_rupee_amount("no amount here") is None
