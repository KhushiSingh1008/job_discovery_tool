from pathlib import Path

import pytest

from app.scraper.cli import main


def test_sources_command_succeeds() -> None:
    assert main(["sources"]) == 0


def test_unknown_source_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--source", "nope"]) == 2
    assert "Unknown source(s): nope" in capsys.readouterr().err


def test_rescore_command_runs_on_empty_database(
    db_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["rescore"]) == 0
    assert "Rescored 0 listings." in capsys.readouterr().out
    assert db_path.exists()
