from datetime import datetime, timezone

from app.core.timeutils import business_date_str, is_late_arrival


def test_london_uses_bst_in_summer():
    summer = datetime(2026, 7, 1, 23, 30, tzinfo=timezone.utc)
    assert business_date_str("Europe/London", summer) == "2026-07-02"


def test_london_uses_gmt_in_winter():
    winter = datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc)
    assert business_date_str("Europe/London", winter) == "2026-01-01"


def test_late_arrival_uses_dst_aware_local_time():
    summer_scan = datetime(2026, 7, 1, 7, 59, tzinfo=timezone.utc)
    winter_scan = datetime(2026, 1, 1, 9, 1, tzinfo=timezone.utc)
    assert is_late_arrival(summer_scan, "09:00", 0, "Europe/London") is False
    assert is_late_arrival(winter_scan, "09:00", 0, "Europe/London") is True


def test_legacy_fixed_offset_still_works():
    instant = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert business_date_str("+05:00", instant) == "2026-01-01"
