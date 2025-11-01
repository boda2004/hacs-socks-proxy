"""Reverse SOCKS5 tunnel integration."""
from __future__ import annotations

import subprocess
import threading
import time
import logging
import os
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "reverse_socks"
_LOGGER = logging.getLogger(__name__)

# Path to the actual Python tunnel script
SCRIPT_PATH = "/config/custom_components/reverse_socks/tunnel.py"

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the reverse SOCKS integration."""
    hass.data[DOMAIN] = {"process": None, "thread": None}

    def _start_tunnel():
        if hass.data[DOMAIN]["process"] and hass.data[DOMAIN]["process"].poll() is None:
            _LOGGER.warning("Tunnel already running")
            return

        cmd = ["python3", SCRIPT_PATH]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        hass.data[DOMAIN]["process"] = proc

        def log_output():
            for line in proc.stdout:
                _LOGGER.info("TUNNEL: %s", line.rstrip())
            proc.wait()
            _LOGGER.error("Tunnel process exited with code %s", proc.returncode)
            hass.data[DOMAIN]["process"] = None

        thread = threading.Thread(target=log_output, daemon=True)
        thread.start()
        hass.data[DOMAIN]["thread"] = thread

        _LOGGER.info("Reverse SOCKS tunnel started")

    def _stop_tunnel():
        proc = hass.data[DOMAIN]["process"]
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            _LOGGER.info("Tunnel stopped")
        hass.data[DOMAIN]["process"] = None

    # Services
    hass.services.register(DOMAIN, "start", lambda call: _start_tunnel())
    hass.services.register(DOMAIN, "stop", lambda call: _stop_tunnel())
    hass.services.register(DOMAIN, "restart", lambda call: (_stop_tunnel(), time.sleep(1), _start_tunnel()))

    # Auto-start on boot
    if config[DOMAIN].get("autostart", False):
        hass.loop.call_soon_threadsafe(_start_tunnel)

    return True
