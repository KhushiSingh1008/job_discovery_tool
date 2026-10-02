import pytest

from app.scraper.cli import main


def test_sources_command_succeeds() -> None:
    assert main(["sources"]) == 0


def test_unknown_source_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--source", "nope"]) == 2
    assert "Unknown source(s): nope" in capsys.readouterr().err
