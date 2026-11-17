import datetime

from app.config import settings
from app.services.video import build_cut_command, build_mock_command
from app.services.video_source_resolver import VideoSourceMatch
from app.timeutils import local_date_key, local_day_start_utc


def test_default_clip_is_5s_before_and_13s_after():
    assert settings.VIDEO_SECONDS_BEFORE == 5
    assert settings.VIDEO_SECONDS_AFTER == 13
    assert settings.clip_duration_seconds == 18


def test_cut_command_uses_offset_and_duration(tmp_path):
    match = VideoSourceMatch(tmp_path / "src.mp4", 295.0, 10.0)
    cmd = build_cut_command(match, tmp_path / "out.mp4")
    assert cmd[cmd.index("-ss") + 1] == "295.000"
    assert cmd[cmd.index("-t") + 1] == "10.000"


def test_mock_video_has_clip_length(tmp_path):
    cmd = build_mock_command(tmp_path / "out.mp4", settings.clip_duration_seconds)
    assert "testsrc=duration=18:size=640x360:rate=25" in cmd


def test_local_day_starts_at_helsinki_midnight():
    # 17.11.2026 klo 01:30 Helsinki = 16.11. klo 23:30 UTC -> päivä on jo 17.11.
    now = datetime.datetime(2026, 11, 16, 23, 30, tzinfo=datetime.timezone.utc)
    assert local_day_start_utc(now) == datetime.datetime(2026, 11, 16, 22, 0)
    assert local_date_key(datetime.datetime(2026, 11, 16, 23, 30)) == "2026-11-17"


def test_local_day_start_summer_time():
    now = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=datetime.timezone.utc)
    assert local_day_start_utc(now) == datetime.datetime(2026, 6, 30, 21, 0)
