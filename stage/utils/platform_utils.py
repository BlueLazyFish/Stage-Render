"""Cross-platform shims — the small per-OS bits we can't avoid.

The addon ships as a single cross-platform bundle; only these shims branch.
Pure stdlib — no extra dependencies.
"""

from __future__ import annotations

import platform as _platform
import shutil
import subprocess
from pathlib import Path

from .logger import get_logger


_log = get_logger()


def is_macos() -> bool:
    return _platform.system() == "Darwin"


def is_windows() -> bool:
    return _platform.system() == "Windows"


def is_linux() -> bool:
    return _platform.system() == "Linux"


def open_in_file_browser(path: str | Path) -> None:
    """Reveal a file or folder in the OS file manager (Finder, Explorer, etc.)."""
    p = Path(path)
    if not p.exists():
        _log.warning("Cannot open %s in file browser — does not exist", p)
        return

    try:
        if is_macos():
            subprocess.run(["open", "-R", str(p)], check=False)
        elif is_windows():
            subprocess.run(["explorer", "/select,", str(p)], check=False)
        else:
            target = p if p.is_dir() else p.parent
            subprocess.run(["xdg-open", str(target)], check=False)
    except FileNotFoundError as e:
        _log.warning("OS file-browser command not found: %s", e)


def notify(title: str, message: str) -> None:
    """Send a desktop notification. Best-effort; silent failure if unavailable."""
    try:
        if is_macos():
            script = f'display notification "{_quote(message)}" with title "{_quote(title)}"'
            subprocess.run(["osascript", "-e", script], check=False)
        elif is_windows():
            # Best-effort: BurntToast PowerShell module if installed.
            # Falls back silently if not — TODO: native WinRT toast in Phase 2.
            ps = (
                "try { Import-Module BurntToast -ErrorAction Stop; "
                f'New-BurntToastNotification -Text "{_quote(title)}", "{_quote(message)}" '
                "} catch { }"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)
        elif is_linux():
            if shutil.which("notify-send"):
                subprocess.run(["notify-send", title, message], check=False)
    except Exception as e:
        _log.warning("Notification failed: %s", e)


def shutdown_system() -> None:
    """Initiate system shutdown. Caller is responsible for confirmation UX."""
    if is_macos():
        subprocess.run(
            ["osascript", "-e", 'tell app "System Events" to shut down'],
            check=False,
        )
    elif is_windows():
        subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
    elif is_linux():
        subprocess.run(["systemctl", "poweroff"], check=False)


def _quote(s: str) -> str:
    """Escape double quotes in user-provided strings before interpolating into shell."""
    return s.replace('"', '\\"')
