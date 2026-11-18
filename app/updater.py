"""Background version checker: GitHub API -> Gitee API fallback.

Runs off the UI thread so startup is never blocked. Emits exactly one of:

- ``update_available(latest, release_url, notes)``  — remote > current
- ``up_to_date(latest)``                            — remote >= current
- ``check_failed(reason)``                          — both endpoints unreachable

The caller decides what to show; this module does no UI on its own.
"""
from __future__ import annotations

import json
import re
from typing import Tuple
from urllib import request

from PySide6.QtCore import QThread, Signal

from . import __version__


# Public release endpoints. Gitee is the China-side mirror; its releases are
# kept in sync with GitHub. Until a Gitee release exists, that endpoint 404s
# and we fall through silently.
GITHUB_LATEST_API = "https://api.github.com/repos/vfaner/muask/releases/latest"
GITEE_LATEST_API = "https://gitee.com/api/v5/repos/super_rgh/muask/releases/latest"

# Where the browser lands when the user clicks the red dot.
GITHUB_RELEASES_PAGE = "https://github.com/vfaner/muask/releases/latest"
GITEE_RELEASES_PAGE = "https://gitee.com/super_rgh/muask/releases/latest"

HTTP_TIMEOUT = 5.0  # seconds per endpoint; GitHub 5s 内没响应就切 Gitee


def parse_semver(s: str) -> Tuple[int, ...]:
    """'v1.4.0' / '1.4.0-rc1' -> (1, 4, 0). Non-numeric suffixes ignored."""
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s or "")
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())


def _http_get_json(url: str, timeout: float = HTTP_TIMEOUT) -> dict:
    req = request.Request(url, headers={
        "User-Agent": "muask-updater",
        "Accept": "application/vnd.github+json",
    })
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class UpdateCheckWorker(QThread):
    """Probe GitHub first, Gitee second; emit exactly one signal on completion."""

    update_available = Signal(str, str, str)   # latest_version, release_url, notes
    up_to_date = Signal(str)                    # latest_version
    check_failed = Signal(str)                  # short reason

    def run(self) -> None:
        sources = [
            (GITHUB_LATEST_API, GITHUB_RELEASES_PAGE),
            (GITEE_LATEST_API, GITEE_RELEASES_PAGE),
        ]
        last_err = "unknown"
        for api_url, page_url in sources:
            try:
                data = _http_get_json(api_url)
                if not isinstance(data, dict):
                    # Captive portal / proxy returned HTTP 200 with non-JSON
                    # shape; try the next source instead of dying silently.
                    raise ValueError("unexpected JSON payload")
                tag = (data.get("tag_name") or "").strip()
                notes = (data.get("body") or "").strip()
                if not tag:
                    raise ValueError("release has no tag_name")
            except Exception as e:  # network / DNS / 404 / timeout — next source
                last_err = f"{type(e).__name__}: {e}"
                continue

            latest = parse_semver(tag)
            current = parse_semver(__version__)
            pretty = tag.lstrip("v")
            if latest > current:
                self.update_available.emit(pretty, page_url, notes)
            else:
                self.up_to_date.emit(pretty)
            return

        self.check_failed.emit(last_err)
