"""Kameratallenteen täsmäys: aikavyöhyke, 5 s + 5 s leike, kesken oleva tallenne, tiedostonvaihto."""
import datetime
from pathlib import Path

import pytest

from app.services.video_source_resolver import SynologyTimestampVideoResolver


def make_files(root: Path, names):
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")


def resolver(root, durations):
    return SynologyTimestampVideoResolver(
        camera_root_path=str(root),
        camera_timezone="Europe/Helsinki",
        max_file_duration_seconds=3600,
        probe=lambda p: durations.get(p.name),
    )


def utc(*args):
    return datetime.datetime(*args)  # naiivi UTC kuten kannassa


def test_filename_timestamp_is_camera_local_time(tmp_path):
    # Kamera nimeää paikallisajassa: 12:00 Helsinki (talviaika, UTC+2) = 10:00 UTC
    make_files(tmp_path, ["CAM01_20261117_120000.mp4"])
    r = resolver(tmp_path, {"CAM01_20261117_120000.mp4": 900.0})
    match = r.resolve_source(utc(2026, 11, 17, 10, 5, 0), 5, 5)
    assert match is not None
    assert match.clip_start_offset_seconds == pytest.approx(295.0)  # 5 min - 5 s
    assert match.duration_seconds == 10.0


def test_utc_interpretation_would_miss(tmp_path):
    # Sama tapahtuma klo 10:05 UTC ei saa osua tiedostoon, joka alkaa 12:00 paikallista (=10:00 UTC) + 2 h
    make_files(tmp_path, ["CAM01_20261117_100000.mp4"])  # 10:00 Helsinki = 08:00 UTC
    r = resolver(tmp_path, {"CAM01_20261117_100000.mp4": 900.0})  # 15 min tiedosto
    assert r.resolve_source(utc(2026, 11, 17, 10, 5, 0), 5, 5) is None


def test_picks_nearest_preceding_file(tmp_path):
    names = ["CAM01_20261117_115000.mp4", "CAM01_20261117_120000.mp4", "CAM01_20261117_121000.mp4"]
    make_files(tmp_path, names)
    r = resolver(tmp_path, {n: 600.0 for n in names})
    match = r.resolve_source(utc(2026, 11, 17, 10, 3, 0), 5, 5)  # 12:03 paikallista
    assert match.file_path.name == "CAM01_20261117_120000.mp4"
    assert match.clip_start_offset_seconds == pytest.approx(175.0)


def test_recording_in_progress_returns_none(tmp_path):
    make_files(tmp_path, ["CAM01_20261117_120000.mp4"])
    r = resolver(tmp_path, {})  # ffprobe ei pysty lukemaan (moov puuttuu)
    assert r.resolve_source(utc(2026, 11, 17, 10, 0, 30), 5, 5) is None


def test_recording_not_long_enough_yet(tmp_path):
    make_files(tmp_path, ["CAM01_20261117_120000.mp4"])
    r = resolver(tmp_path, {"CAM01_20261117_120000.mp4": 30.0})
    # Leike tarvitsee 28 s..38 s, tiedosto 30 s eikä uudempaa ole -> odotetaan
    assert r.resolve_source(utc(2026, 11, 17, 10, 0, 33), 5, 5) is None


def test_rollover_gives_partial_clip(tmp_path):
    names = ["CAM01_20261117_120000.mp4", "CAM01_20261117_120100.mp4"]
    make_files(tmp_path, names)
    r = resolver(tmp_path, {names[0]: 60.0, names[1]: 60.0})
    match = r.resolve_source(utc(2026, 11, 17, 10, 0, 58), 5, 5)  # 53..63 s
    assert match.file_path.name == names[0]
    assert match.partial is True
    assert match.duration_seconds == pytest.approx(7.0)


def test_synology_surveillance_layout(tmp_path):
    make_files(tmp_path, [
        "Talli-kamera/20261117AM/Talli-kamera-20261117-095959-1795420799.mp4",
        "Talli-kamera/20261116PM/Talli-kamera-20261116-235959-1795384799.mp4",
    ])
    r = resolver(tmp_path, {"Talli-kamera-20261117-095959-1795420799.mp4": 1800.0})
    match = r.resolve_source(utc(2026, 11, 17, 8, 10, 0), 5, 5)  # 10:10 paikallista
    assert match is not None
    assert match.file_path.name.startswith("Talli-kamera-20261117-095959")


def test_old_files_outside_max_duration_ignored(tmp_path):
    make_files(tmp_path, ["CAM01_20261117_080000.mp4"])
    r = resolver(tmp_path, {"CAM01_20261117_080000.mp4": 99999.0})
    assert r.resolve_source(utc(2026, 11, 17, 10, 0, 0), 5, 5) is None
