import json
import os

_PATH = os.path.expanduser("~/.config/bluetooth-audio-connector/settings.json")

_DEFAULTS = {
    "auto_reconnect": False,
    "last_devices": [],
}


def load():
    try:
        with open(_PATH) as f:
            return {**_DEFAULTS, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULTS.copy()


def save(data):
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    with open(_PATH, "w") as f:
        json.dump(data, f, indent=2)
