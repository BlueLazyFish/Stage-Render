"""Post-render action execution.

run_actions(scene, studio, output_path) walks studio.post_render_actions
in declared order and executes each. Per the plan §3 v1.0, the order is
significant — MOVE before COPY breaks the chain because the source no
longer exists.

Each runner:
- Catches and logs its own exceptions so one bad action doesn't abort
  the rest of the chain
- Expands path templates via stage.core.paths.expand_path so {studio},
  {frame}, {date_time}, etc. work consistently with output_override
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib import error as urlerror, request as urlrequest

import bpy

from .paths import build_default_context, expand_path
from ..utils.logger import get_logger
from ..utils.platform_utils import is_linux, is_macos, is_windows


_log = get_logger()


def _build_ctx(scene, studio, output_path: str) -> dict[str, Any]:
    """Path-expansion context for post-render action targets / messages."""
    ctx = build_default_context(
        studio_name=studio.name,
        blend_path=bpy.data.filepath,
        scene=scene,
        frame=scene.frame_current,
    )
    ctx["output_path"] = output_path
    return ctx


def _expanded(template: str, scene, studio, output_path: str) -> str:
    return expand_path(template, _build_ctx(scene, studio, output_path))


def _expanded_message(template: str, scene, studio, output_path: str) -> str:
    """Like _expanded but skips path-safety sanitization — message values
    keep their slashes / colons / spaces."""
    return expand_path(template, _build_ctx(scene, studio, output_path), sanitize=False)


# --- per-type runners ------------------------------------------------------


def copy_file(action, scene, studio, output_path: str) -> None:
    if not output_path or not Path(output_path).exists():
        _log.warning("COPY_FILE: source missing: %s", output_path)
        return
    dst = _expanded(action.target, scene, studio, output_path)
    if not dst:
        return
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_path, dst)
    _log.info("COPY_FILE: %s -> %s", output_path, dst)


def move_file(action, scene, studio, output_path: str) -> None:
    if not output_path or not Path(output_path).exists():
        _log.warning("MOVE_FILE: source missing: %s", output_path)
        return
    dst = _expanded(action.target, scene, studio, output_path)
    if not dst:
        return
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(output_path, dst)
    _log.info("MOVE_FILE: %s -> %s", output_path, dst)


def delete_folder(action, scene, studio, output_path: str) -> None:
    folder = _expanded(action.target, scene, studio, output_path)
    if not folder:
        return
    p = Path(folder)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
        _log.info("DELETE_FOLDER: removed %s", p)


def play_sound(action, scene, studio, output_path: str) -> None:
    sound = _expanded(action.target or "", scene, studio, output_path)
    if not sound or sound.lower() == "default":
        # System bell — best-effort; some terminals don't render \a
        import sys
        sys.stdout.write("\a")
        sys.stdout.flush()
        return
    if not Path(sound).exists():
        _log.warning("PLAY_SOUND: file missing: %s", sound)
        return
    try:
        if is_macos():
            subprocess.run(["afplay", sound], check=False)
        elif is_linux():
            for cmd in ("paplay", "aplay", "ffplay"):
                if shutil.which(cmd):
                    subprocess.run([cmd, "-q", sound], check=False)
                    break
        elif is_windows():
            try:
                import winsound
                winsound.PlaySound(sound, winsound.SND_FILENAME)
            except ImportError:
                pass
    except Exception as e:
        _log.warning("PLAY_SOUND failed: %s", e)


_DEFAULT_SLACK_MESSAGE = "Render complete: {studio} -> {output_path}"


def slack_webhook(action, scene, studio, output_path: str) -> None:
    url = action.target.strip()
    if not url:
        _log.warning("SLACK_WEBHOOK: empty URL")
        return
    template = action.message or _DEFAULT_SLACK_MESSAGE
    text = _expanded_message(template, scene, studio, output_path)
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urlrequest.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        urlrequest.urlopen(req, timeout=10)
        _log.info("SLACK_WEBHOOK: posted %r", text)
    except (urlerror.URLError, TimeoutError) as e:
        _log.warning("SLACK_WEBHOOK failed: %s", e)


_RUNNERS = {
    'COPY_FILE': copy_file,
    'MOVE_FILE': move_file,
    'DELETE_FOLDER': delete_folder,
    'PLAY_SOUND': play_sound,
    'SLACK_WEBHOOK': slack_webhook,
}


def run_actions(scene, studio, output_path: str) -> None:
    """Walk studio.post_render_actions and execute each in order.

    Per-action exceptions are logged and swallowed so one bad action
    doesn't abort the rest of the chain.
    """
    for action in studio.post_render_actions:
        runner = _RUNNERS.get(action.action_type)
        if runner is None:
            _log.warning("Unknown post-render action type: %s", action.action_type)
            continue
        try:
            runner(action, scene, studio, output_path)
        except Exception as e:
            _log.warning(
                "Post-render action %s failed: %s",
                action.action_type, e,
            )
