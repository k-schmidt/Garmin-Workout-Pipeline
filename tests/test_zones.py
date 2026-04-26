"""Tests for zone resolver."""

from pathlib import Path

import pytest

from garmin_pipeline.zones import (
    ZoneConfig,
    load_zones,
    pace_to_mps,
    resolve_zone,
)

ZONES_FILE = Path(__file__).parent.parent / "workouts" / "zones.yaml"


class TestPaceConversion:
    def test_5min_km(self) -> None:
        assert pace_to_mps("5:00") == pytest.approx(3.333, rel=1e-2)

    def test_4min_30s_km(self) -> None:
        assert pace_to_mps("4:30") == pytest.approx(3.704, rel=1e-2)

    def test_zero_pace_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be zero"):
            pace_to_mps("0:00")


class TestLoadZones:
    def test_load(self) -> None:
        config = load_zones(ZONES_FILE)
        assert config.updated == "2026-04-26"
        assert "z2" in config.running.hr_zones
        assert config.cycling.ftp == 220

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("")
        config = load_zones(f)
        assert isinstance(config, ZoneConfig)


class TestResolveZone:
    @pytest.fixture()
    def config(self) -> ZoneConfig:
        return load_zones(ZONES_FILE)

    def test_running_pace_zone(self, config: ZoneConfig) -> None:
        result = resolve_zone("running", "threshold", config)
        assert result["targetType"]["workoutTargetTypeKey"] == "pace.zone"
        assert result["targetValueOne"] is not None
        assert result["targetValueTwo"] is not None
        # Faster pace → higher speed → targetValueTwo
        assert result["targetValueTwo"] > result["targetValueOne"]

    def test_running_hr_fallback(self, config: ZoneConfig) -> None:
        # "aerobic" is in both hr and pace; force HR override to test fallback
        result = resolve_zone("running", "aerobic", config, target_type_override="heart_rate")
        assert result["targetType"]["workoutTargetTypeKey"] == "heart.rate.zone"
        assert result["targetValueOne"] == 146.0
        assert result["targetValueTwo"] == 151.0

    def test_running_explicit_hr(self, config: ZoneConfig) -> None:
        result = resolve_zone("running", "z2", config, target_type_override="heart_rate")
        assert result["targetType"]["workoutTargetTypeKey"] == "heart.rate.zone"

    def test_cycling_power_zone(self, config: ZoneConfig) -> None:
        result = resolve_zone("cycling", "threshold", config)
        assert result["targetType"]["workoutTargetTypeKey"] == "power.zone"
        # FTP 220, threshold 91-105%
        assert result["targetValueOne"] == pytest.approx(200.2)
        assert result["targetValueTwo"] == pytest.approx(231.0)

    def test_strength_returns_no_target(self, config: ZoneConfig) -> None:
        result = resolve_zone("strength", "anything", config)
        assert result["targetType"]["workoutTargetTypeKey"] == "no.target"

    def test_unknown_running_zone_raises(self, config: ZoneConfig) -> None:
        with pytest.raises(KeyError, match="Unknown running zone"):
            resolve_zone("running", "nonexistent", config)

    def test_unknown_cycling_zone_raises(self, config: ZoneConfig) -> None:
        with pytest.raises(KeyError, match="Unknown cycling zone"):
            resolve_zone("cycling", "nonexistent", config)
