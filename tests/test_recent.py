"""Tests for news filtering, results comparison and management-change flags."""

from datetime import date, datetime, timezone

from scorecard.recent import (clean_news, is_relevant, officers_from_info, recent_flags,
                              results_summary, tag_headline, update_officers)

TODAY = date(2026, 10, 28)


def ts(d: str) -> int:
    return int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp())


def test_tags():
    assert "Profit warning" in tag_headline("Howden cuts full-year guidance as demand slows")
    assert "Management change" in tag_headline("WPP chief executive to step down after two years")
    assert "Management change" in tag_headline("Tesco appoints new CFO")
    assert "Deal" in tag_headline("Rival weighs takeover bid for Auto Trader")
    assert "Results" in tag_headline("NEXT H1 Earnings Call Highlights")
    assert tag_headline("Tesco PLC's Dividend Analysis") == []


def test_relevance_keeps_tagged_and_drops_roundups():
    assert is_relevant({"title": "Next raises guidance", "relatedTickers": ["NXT.L"]}, "NXT.L", "Next")
    assert not is_relevant({"title": "Howden Joinery And 2 Other British Undervalued Stocks", "relatedTickers": ["HWDN.L"]},
                           "HWDN.L", "Howden Joinery")
    assert not is_relevant({"title": "Sainsbury's downgraded", "relatedTickers": ["SBRY.L"]}, "TSCO.L", "Tesco")
    # Dual-listed: tagged with the US symbol, accepted only if the name appears
    assert is_relevant({"title": "Shell adds production", "relatedTickers": ["SHEL"]}, "SHEL.L", "Shell")
    assert not is_relevant({"title": "Oil majors rally", "relatedTickers": ["SHEL"]}, "SHEL.L", "Shell")


def test_clean_news_drops_old_and_duplicate():
    items = [
        {"title": "Tesco results", "relatedTickers": ["TSCO.L"], "providerPublishTime": ts("2026-10-08")},
        {"title": "Tesco results", "relatedTickers": ["TSCO.L"], "providerPublishTime": ts("2026-10-07")},
        {"title": "Old news", "relatedTickers": ["TSCO.L"], "providerPublishTime": ts("2026-05-01")},
    ]
    out = clean_news(items, "TSCO.L", "Tesco", TODAY)
    assert [h["date"] for h in out] == ["2026-10-08"]


def test_margin_drop_since_annual_is_a_red_flag():
    r = results_summary({"operatingMargins": 0.118}, 0.147, TODAY)
    f = recent_flags(r, [], {}, TODAY)
    assert any("down from 14.7%" in x for x in f["red_flags"])


def test_small_margin_move_is_ignored():
    r = results_summary({"operatingMargins": 0.0468, "revenueGrowth": 0.04}, 0.0421, TODAY)
    f = recent_flags(r, [], {}, TODAY)
    assert f == {"strengths": [], "red_flags": [], "notes": []}


def test_results_dates_split_into_last_and_next():
    r = results_summary({"earningsTimestampStart": ts("2026-10-30"), "lastFiscalYearEnd": ts("2026-03-31"),
                         "mostRecentQuarter": ts("2026-06-30")}, None, TODAY)
    assert r["next_results"] == "2026-10-30" and r["last_results"] is None and r["newer_than_annual"]
    assert any("Results due 30 October" in n for n in recent_flags(r, [], {}, TODAY)["notes"])


def test_officer_change_is_flagged_for_a_year():
    saved = update_officers({"ceo": "A Smith"}, {}, date(2026, 1, 1))
    assert saved["ceo"]["since"] is None  # already there when tracking began
    changed = update_officers({"ceo": "B Jones"}, saved, date(2026, 10, 1))
    assert changed["ceo"] == {"name": "B Jones", "since": "2026-10-01", "previous": "A Smith"}
    assert any("New chief executive: B Jones" in n for n in recent_flags(None, [], changed, TODAY)["notes"])
    assert recent_flags(None, [], changed, date(2027, 11, 1))["notes"] == []


def test_officers_from_titles():
    info = {"companyOfficers": [{"name": "Mr. Ken  Murphy", "title": "Group CEO & Executive Director"},
                                {"name": "Deputy", "title": "Deputy CEO"},
                                {"name": "Mr. Imran Nawaz", "title": "CFO & Director"}]}
    assert officers_from_info(info) == {"ceo": "Mr. Ken Murphy", "cfo": "Mr. Imran Nawaz"}


def test_old_alert_headlines_do_not_warn():
    news = [{"date": "2026-08-01", "title": "Tesco CEO to step down", "tags": ["Management change"]}]
    assert recent_flags(None, news, {}, TODAY)["notes"] == []


def test_stale_results_date_is_dropped():
    r = results_summary({"earningsTimestamp": ts("2026-02-26"), "mostRecentQuarter": ts("2026-06-13")}, None, TODAY)
    assert r["last_results"] is None
