import pytest
from app.services.video import validate_and_resolve_video_path


def test_validate_and_resolve_video_path_traversal():
    """Varmistaa, että suhteellisen polun karkaamisyritykset heittävät poikkeuksen."""
    with pytest.raises(ValueError):
        validate_and_resolve_video_path("../../etc/shadow")

    with pytest.raises(ValueError):
        validate_and_resolve_video_path("../secret.key")

    with pytest.raises(ValueError):
        validate_and_resolve_video_path("/volume1/surveillance")


def test_validate_and_resolve_video_path_valid():
    """Sallittu polku hyväksytään."""
    valid_rel = "1/2026/11/event_123.mp4"
    resolved = validate_and_resolve_video_path(valid_rel)
    assert resolved.name == "event_123.mp4"
