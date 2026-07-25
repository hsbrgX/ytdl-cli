import json
import os
import urllib.request
import urllib.error
from config.constants import APP_DIR

VERSION_PATH = os.path.join(APP_DIR, "version.json")

DEFAULT_VERSION = {
    "owner": "hsbrgX",
    "repo": "ytdl-cli",
    "version": "1.0",
    "branch": "main",
}


def load_version():
    if not os.path.isfile(VERSION_PATH):
        return dict(DEFAULT_VERSION)
    try:
        with open(VERSION_PATH, "r", encoding="utf-8") as f:
            return {**DEFAULT_VERSION, **json.load(f)}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_VERSION)


def get_remote_version(owner, repo, branch):
    url = f"https://raw.githubusercontent.com/hsbrgX/ytdl-cli/main/version.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        return None
