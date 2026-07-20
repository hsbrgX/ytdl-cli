import os
import sys
import curses
import shutil
from config.constants import RESET, BOLD, CYAN, GREEN, YELLOW, BLUE, MAGENTA, RED, GRAY, BAR_WIDTH
import core.debug_log as debug_log

ASCII_LOGO = r"""
    ██╗   ██╗████████╗██████╗ ██╗
    ╚██╗ ██╔╝╚══██╔══╝██╔══██╗██║
     ╚████╔╝    ██║   ██║  ██║██║
      ╚██╔╝     ██║   ██║  ██║██║
       ██║      ██║   ██████╔╝███████╗
       ╚═╝      ╚═╝   ╚═════╝ ╚══════╝
"""


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def banner(text=None):
    print(f"{CYAN}{ASCII_LOGO}{RESET}")
    if text:
        width = min(shutil.get_terminal_size((60, 20)).columns, 60)
        print(f"{BOLD}{MAGENTA}{text.center(width)}{RESET}")
        print(f"{CYAN}{'─' * width}{RESET}")
        debug_log.log_debug("BANNER", text)


def info(msg):
    print(f"{BLUE}::{RESET} {msg}")
    debug_log.log_debug("INFO", msg)


def ok(msg):
    print(f"{GREEN}✓{RESET} {msg}")
    debug_log.log_debug("SUCCESS", msg)


def warn(msg):
    print(f"{YELLOW}!{RESET} {msg}")
    debug_log.log_debug("WARNING", msg)


def err(msg):
    print(f"{RED}✗{RESET} {msg}")
    debug_log.log_debug("ERROR", msg)


def found(count, seconds):
    msg = f"Found {count} in {seconds:.3f}s"
    print(f"{GREEN}{msg}{RESET}")
    debug_log.log_debug("SEARCH", msg)


def prompt(label):
    val = input(f"{CYAN}» {label}{RESET}").strip()
    debug_log.log_debug("PROMPT", f"Label: '{label}' | Input: '{val}'")
    return val


def render_progress_bar(percent, extra=""):
    filled = int(BAR_WIDTH * percent / 100)
    bar = "#" * filled + " " * (BAR_WIDTH - filled)
    sys.stdout.write(f"\r[{GREEN}{bar}{RESET}] {percent:3.0f}% {GRAY}{extra}{RESET}")
    sys.stdout.flush()


def build_home_header(version_info, user_name, first_login, download_dir):
    width = 46
    top = "╔" + "═" * (width - 2) + "╗"
    bot = "╚" + "═" * (width - 2) + "╝"
    sep = "╟" + "─" * (width - 2) + "╢"

    def row(text):
        return "║ " + text[: width - 4].ljust(width - 4) + " ║"

    logo_rows = [row(line) for line in ASCII_LOGO.strip("\n").split("\n")]
    lines = [top, *logo_rows, sep]
    lines.append(row(f"v{version_info['version']}  ·  {version_info['owner']}/{version_info['repo']}"))
    lines.append(sep)
    lines.append(row(f"Halo, {user_name}"))
    lines.append(row(f"First login: {first_login}"))
    lines.append(row(f"Dir: {download_dir}"))
    lines.append(bot)
    lines.append("")
    return lines


class GoHome(Exception):
    pass


_UP_KEYS = (curses.KEY_UP, ord("w"), ord("W"), ord("k"))
_DOWN_KEYS = (curses.KEY_DOWN, ord("s"), ord("S"), ord("j"))
_LEFT_KEYS = (curses.KEY_LEFT, ord("a"), ord("A"), ord("h"))
_RIGHT_KEYS = (curses.KEY_RIGHT, ord("d"), ord("D"), ord("l"))
_CONFIRM_KEYS = (curses.KEY_ENTER, 10, 13)
_CANCEL_KEYS = (ord("q"), ord("Q"), 27)
_HOME_KEY = 8


def arrow_select(options, header_lines=None, footer="↑/w ↓/s  Enter pilih  q batal  ^H home"):
    header_lines = header_lines or []

    def _run(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        idx, top = 0, 0

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        header_attr = curses.color_pair(1) | curses.A_BOLD
        select_attr = curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD
        footer_attr = curses.color_pair(2)

        while True:
            height, width = stdscr.getmaxyx()
            header_h = len(header_lines)
            visible = max(height - header_h - 2, 1)

            if idx < top:
                top = idx
            elif idx >= top + visible:
                top = idx - visible + 1

            stdscr.clear()
            for row, line in enumerate(header_lines):
                stdscr.addstr(row, 0, line[: width - 1], header_attr)

            for row, i in enumerate(range(top, min(top + visible, len(options)))):
                marker = "▶ " if i == idx else "  "
                attr = select_attr if i == idx else curses.A_NORMAL
                stdscr.addstr(header_h + row, 0, f"{marker}{options[i]}"[: width - 1], attr)

            stdscr.addstr(height - 1, 0, footer[: width - 1], footer_attr)
            stdscr.refresh()

            key = stdscr.getch()
            if key == _HOME_KEY:
                debug_log.log_debug("SELECT", "User menekan ^H (GoHome)")
                raise GoHome()
            elif key in _UP_KEYS:
                idx = (idx - 1) % len(options)
            elif key in _DOWN_KEYS:
                idx = (idx + 1) % len(options)
            elif key == curses.KEY_NPAGE:
                idx = min(idx + visible, len(options) - 1)
            elif key == curses.KEY_PPAGE:
                idx = max(idx - visible, 0)
            elif key in _CONFIRM_KEYS or key in _RIGHT_KEYS:
                debug_log.log_debug("SELECT", f"Pilihan terpilih: idx {idx} -> '{options[idx]}'")
                return idx
            elif key in _CANCEL_KEYS or key in _LEFT_KEYS:
                debug_log.log_debug("SELECT", "User membatalkan pilihan (Cancel/Q/Esc)")
                return None

    return curses.wrapper(_run)