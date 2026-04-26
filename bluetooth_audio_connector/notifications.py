import logging
import gi

log = logging.getLogger(__name__)
_available = False

try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify
    Notify.init("soundbridge")
    _available = True
except Exception as e:
    log.warning("Desktop notifications unavailable: %s", e)


def _send(summary, body, icon):
    if not _available:
        log.info("%s: %s", summary, body)
        return
    try:
        Notify.Notification.new(summary, body, icon).show()
    except Exception as e:
        log.warning("Notification failed: %s", e)


def device_connected(name):
    _send("soundbridge", f"{name} connected", "bluetooth-active")


def device_disconnected(name):
    _send("soundbridge", f"{name} disconnected", "bluetooth")
