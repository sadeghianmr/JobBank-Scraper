"""Shared helpers for reading per-user YAML configuration."""

from typing import Any

import yaml

from src.config import (
    DEFAULT_USER_LIMIT_REQUEST,
    MAX_USER_LIMIT_REQUEST,
    MIN_USER_LIMIT_REQUEST,
    USER_CONFIGS_DIR,
)


def normalize_user_limit_request(value: Any) -> int:
    """Return a valid request limit, falling back to the project default."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return DEFAULT_USER_LIMIT_REQUEST

    if limit < MIN_USER_LIMIT_REQUEST:
        return MIN_USER_LIMIT_REQUEST
    if limit > MAX_USER_LIMIT_REQUEST:
        return MAX_USER_LIMIT_REQUEST
    return limit


def load_user_config(user_id: int) -> dict[str, Any]:
    """Load a user's YAML config, returning an empty config when it is missing."""
    config_path = USER_CONFIGS_DIR / f"user_{user_id}.yaml"
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception:
        return {}

    return config if isinstance(config, dict) else {}


def get_user_limit_request(user_id: int) -> int:
    """Read user_limit_request from the user's YAML config."""
    config = load_user_config(user_id)
    return normalize_user_limit_request(config.get("user_limit_request"))
