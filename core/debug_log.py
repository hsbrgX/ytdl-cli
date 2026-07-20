import os
import sys
import time
import atexit
import traceback
from datetime import datetime
from config.constants import APP_DIR

DEBUG_LOG_PATH = os.path.join(APP_DIR, "debug.log")
_IS_ENABLED = False
_START_TIME = None


def init_debugger(enabled):
    global _IS_ENABLED, _START_TIME
    _IS_ENABLED = enabled
    if not _IS_ENABLED:
        return

    _START_TIME = time.perf_counter()
    _write("\n" + "=" * 50)
    _write(f"[START] Sesi Debug dimulai pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _write(f"[INFO] OS: {os.name} | Python: {sys.version.split()[0]}")
    
    atexit.register(_on_exit)
    sys.excepthook = _handle_exception


def log_debug(category, message):
    if not _IS_ENABLED:
        return
    elapsed = time.perf_counter() - _START_TIME if _START_TIME else 0.0
    timestamp = datetime.now().strftime("%H:%M:%S")
    _write(f"[{timestamp}] (+{elapsed:.2f}s) [{category.upper()}] {message}")


def log_exception(err_msg, exc_info=None):
    if not _IS_ENABLED:
        return
    log_debug("ERROR", err_msg)
    if exc_info:
        tb_lines = traceback.format_exception(*exc_info)
        _write("".join(tb_lines))
    else:
        _write(traceback.format_exc())


def _on_exit():
    if not _IS_ENABLED:
        return
    elapsed = time.perf_counter() - _START_TIME if _START_TIME else 0.0
    _write(f"[EXIT] Sesi berakhir/dihentikan (Durasi: {elapsed:.2f}s)")
    _write("=" * 50 + "\n")


def _handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        log_debug("ABORT", "Script dihentikan paksa oleh user (KeyboardInterrupt / Ctrl+C)")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    log_debug("CRASH", f"Fatal Uncaught Exception: {exc_value}")
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    _write("".join(tb_lines))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def _write(text):
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass