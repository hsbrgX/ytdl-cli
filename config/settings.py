import json
import os
from config.constants import SETTINGS_PATH, DEFAULT_SETTINGS


def load_settings():
    if not os.path.isfile(SETTINGS_PATH):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_SETTINGS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def update_setting(key, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
    return settings