"""Tests for matching companies to Trading 212 instruments (using a made-up instrument list)."""

import pandas as pd

from scorecard.trading212 import match_instruments, symbol_variants

UNIVERSE = pd.DataFrame({
    "ticker": ["TSCO.L", "BT-A.L", "RR.L", "XYZ.L"],
    "name": ["Tesco", "BT Group", "Rolls-Royce", "Not listed plc"],
})

INSTRUMENTS = [
    {"ticker": "TSCOl_EQ", "type": "STOCK", "currencyCode": "GBX", "shortName": "TSCO", "name": "Tesco"},
    {"ticker": "BT.Al_EQ", "type": "STOCK", "currencyCode": "GBX", "shortName": "BT.A", "name": "BT Group"},
    {"ticker": "RRl_EQ", "type": "STOCK", "currencyCode": "GBX", "shortName": "RR.", "name": "Rolls-Royce Holdings"},
    # A US listing with a clashing symbol must not count as the London share
    {"ticker": "XYZ_US_EQ", "type": "STOCK", "currencyCode": "USD", "shortName": "XYZ", "name": "XYZ Inc"},
    # An ETF is not a share in the company
    {"ticker": "TSCOETFl_EQ", "type": "ETF", "currencyCode": "GBX", "shortName": "TSCO", "name": "Some ETF"},
]


def test_symbol_variants_cover_share_classes():
    assert {"BT-A", "BT.A"} <= symbol_variants("BT-A.L")


def test_matching():
    result = match_instruments(UNIVERSE, INSTRUMENTS).set_index("name")["available"]
    assert result["Tesco"] == "yes"
    assert result["BT Group"] == "yes"
    assert result["Rolls-Royce"] == "yes"       # matched on the RRl_EQ ticker even though shortName differs
    assert result["Not listed plc"] == "no"     # the US listing doesn't count
