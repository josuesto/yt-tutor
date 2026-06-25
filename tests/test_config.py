from pathlib import Path

from yt_tutor import config


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("YT_TUTOR_DATA_DIR", str(tmp_path / "d"))
    assert config.data_dir() == (tmp_path / "d")
    assert config.db_path() == (tmp_path / "d" / "watcher.db")


def test_default_is_a_stable_absolute_dir_not_cwd_relative(monkeypatch):
    monkeypatch.delenv("YT_TUTOR_DATA_DIR", raising=False)
    d = config.data_dir()
    # a stable per-user location, not the old cwd-relative "data"
    assert d.is_absolute()
    assert d.name == "yt-tutor"
    assert d != Path("data")
