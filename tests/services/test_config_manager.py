"""Tests for Telegram bot user configuration helpers."""

from datetime import datetime, timedelta, timezone

import yaml

from bot.services.config_manager import ConfigManager


def test_list_configured_user_ids_only_returns_users_with_channels(tmp_path):
    users_dir = tmp_path / "user_configs"
    manager = ConfigManager(users_dir=users_dir)

    manager.save_user_config(1001, {"channel_id": "@jobs", "searches": []})
    manager.save_user_config(1002, {"channel_id": None, "searches": []})
    (users_dir / "user_invalid.yaml").write_text("channel_id: '@bad'\n", encoding="utf-8")

    assert manager.list_user_ids() == [1001, 1002]
    assert manager.list_configured_user_ids() == [1001]


def test_empty_user_config_does_not_break_user_listing(tmp_path):
    users_dir = tmp_path / "user_configs"
    manager = ConfigManager(users_dir=users_dir)

    manager.get_user_config_path(1001).write_text("", encoding="utf-8")

    assert manager.list_user_ids() == [1001]
    assert manager.list_configured_user_ids() == []


def test_old_user_config_gets_scraping_defaults(tmp_path):
    users_dir = tmp_path / "user_configs"
    manager = ConfigManager(users_dir=users_dir)
    manager.save_user_config(
        1001,
        {
            "channel_id": "@jobs",
            "scraping": {
                "interval_hours": 12,
                "headless": True,
                "job_bank_only": True,
            },
            "searches": [{"keyword": "python"}],
        },
    )

    config = manager.load_user_config(1001)
    saved = yaml.safe_load(manager.get_user_config_path(1001).read_text(encoding="utf-8"))

    assert config["scraping"]["last_job_search_at"] is None
    assert config["scraping"]["recent_jobs_only"] is True
    assert saved["scraping"]["last_job_search_at"] is None
    assert saved["scraping"]["recent_jobs_only"] is True


def test_job_search_is_due_when_timestamp_is_missing(tmp_path):
    manager = ConfigManager(users_dir=tmp_path / "user_configs")
    manager.save_user_config(
        1001,
        {
            "channel_id": "@jobs",
            "scraping": {"interval_hours": 2},
            "searches": [{"keyword": "python"}],
        },
    )

    assert manager.is_job_search_due(1001) is True


def test_job_search_due_uses_interval_and_last_search_time(tmp_path):
    manager = ConfigManager(users_dir=tmp_path / "user_configs")
    now = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)

    manager.save_user_config(
        1001,
        {
            "channel_id": "@jobs",
            "scraping": {
                "interval_hours": 2,
                "last_job_search_at": (now - timedelta(hours=3)).isoformat(),
            },
            "searches": [{"keyword": "python"}],
        },
    )

    assert manager.is_job_search_due(1001, now=now) is True

    manager.update_config_field(
        1001,
        "scraping.last_job_search_at",
        (now - timedelta(minutes=30)).isoformat(),
    )

    assert manager.is_job_search_due(1001, now=now) is False


def test_mark_job_search_completed_saves_utc_timestamp(tmp_path):
    manager = ConfigManager(users_dir=tmp_path / "user_configs")
    when = datetime(2026, 5, 6, 12, 30, 45, tzinfo=timezone.utc)

    manager.save_user_config(
        1001,
        {
            "channel_id": "@jobs",
            "scraping": {"interval_hours": 1},
            "searches": [{"keyword": "python"}],
        },
    )

    manager.mark_job_search_completed(1001, when=when)

    config_path = manager.get_user_config_path(1001)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["scraping"]["last_job_search_at"] == "2026-05-06T12:30:45+00:00"
    assert manager.get_last_job_search_at(1001) == when
