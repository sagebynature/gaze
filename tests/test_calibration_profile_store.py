from __future__ import annotations

import json
from pathlib import Path

from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot
from gaze.core.state import CalibrationStatus
from gaze.tracking.calibration import CalibrationResult


def layout(display_id: int = 1, *, x: float = 0) -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=display_id,
                x=x,
                y=0,
                width=1440,
                height=900,
                scale=2.0,
                built_in=True,
            ),
        )
    )


def test_last_good_calibration_store_writes_scalar_profile_only(tmp_path: Path) -> None:
    from gaze.settings.calibration_profile import LastGoodCalibrationStore

    store = LastGoodCalibrationStore(tmp_path / "calibration.json")
    store.save(CalibrationResult.ready(display_layout=layout()))

    payload = json.loads((tmp_path / "calibration.json").read_text(encoding="utf-8"))

    assert payload == {
        "schema_version": "gaze.last-good-calibration.v1",
        "calibration_state": "ready",
        "display_layout_signature": layout().signature,
    }
    assert "title" not in repr(payload).lower()
    assert "screenshot" not in repr(payload).lower()
    assert "frame" not in repr(payload).lower()


def test_last_good_calibration_store_restores_degraded_when_layout_matches(
    tmp_path: Path,
) -> None:
    from gaze.settings.calibration_profile import LastGoodCalibrationStore

    store = LastGoodCalibrationStore(tmp_path / "calibration.json")
    store.save(CalibrationResult.ready(display_layout=layout()))

    restored = store.restore_for_layout(layout())

    assert restored is not None
    assert restored.status is CalibrationStatus.DEGRADED
    assert restored.camera_available is True
    assert restored.tracker_available is True
    assert restored.display_layout == layout()
    assert restored.message == "Calibration restored; fresh sample required"


def test_last_good_calibration_store_does_not_restore_when_layout_changes(
    tmp_path: Path,
) -> None:
    from gaze.settings.calibration_profile import LastGoodCalibrationStore

    store = LastGoodCalibrationStore(tmp_path / "calibration.json")
    store.save(CalibrationResult.ready(display_layout=layout()))

    assert store.restore_for_layout(layout(display_id=2)) is None


def test_last_good_calibration_store_ignores_retry_required_results(tmp_path: Path) -> None:
    from gaze.settings.calibration_profile import LastGoodCalibrationStore

    store = LastGoodCalibrationStore(tmp_path / "calibration.json")
    store.save(CalibrationResult.retry_required("try again"))

    assert not (tmp_path / "calibration.json").exists()
