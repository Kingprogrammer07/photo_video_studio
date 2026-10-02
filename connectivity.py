"""Small online/offline checks for the desktop app."""

from __future__ import annotations

import socket
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectivityStatus:
    online: bool
    message: str


def check_online(timeout: float = 3.0) -> ConnectivityStatus:
    """Return current internet status without raising to the UI."""
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=timeout).close()
    except OSError:
        return ConnectivityStatus(False, "Offline")

    try:
        request = urllib.request.Request(
            "https://api.github.com", headers={"User-Agent": "PhotoVideoStudio"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if 200 <= response.status < 500:
                return ConnectivityStatus(True, "Online")
    except Exception:
        # DNS/socket worked, so treat this as limited but usable internet.
        return ConnectivityStatus(True, "Online")
    return ConnectivityStatus(False, "Offline")
