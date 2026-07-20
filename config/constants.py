import os

if os.name == "nt":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RED = "\033[31m"
GRAY = "\033[90m"

SEARCH_MAX_RESULTS = 100
CHANNEL_MAX_RESULTS = 100
PAGE_SIZE = 25
BAR_WIDTH = 24

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(APP_DIR, "config")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

REPO_URL = "https://github.com/hsbrgX/ytdl-cli.git"
REPO_BRANCH = "main"

DEFAULT_SETTINGS = {
    "download_dir": None,
    "default_format": None,
    "country": "ID",
    "user_name": None,
    "first_login": None,
    "debug_mode": False,
}
