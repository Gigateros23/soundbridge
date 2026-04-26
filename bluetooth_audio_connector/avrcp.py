import logging
from gi.repository import GLib
from ._utils import unpack, unpack_props

BLUEZ_SERVICE = "org.bluez"
PLAYER_IFACE = "org.bluez.MediaPlayer1"
PROPS_IFACE = "org.freedesktop.DBus.Properties"

log = logging.getLogger(__name__)


class AVRCPPlayer:
    def __init__(self, bus, path):
        self._path = path
        self._player = bus.get_proxy(BLUEZ_SERVICE, path, PLAYER_IFACE)
        self._props = bus.get_proxy(BLUEZ_SERVICE, path, PROPS_IFACE)
        self.on_track_changed = None
        self.on_status_changed = None
        self._props.PropertiesChanged.connect(self._on_changed)

    def _on_changed(self, iface, changed, _inv):
        if iface != PLAYER_IFACE:
            return
        changed = unpack_props(changed)
        if "Track" in changed and self.on_track_changed:
            GLib.idle_add(self.on_track_changed, dict(changed["Track"]))
        if "Status" in changed and self.on_status_changed:
            GLib.idle_add(self.on_status_changed, changed["Status"])

    def get_track(self):
        try:
            raw = self._props.Get(PLAYER_IFACE, "Track")
            return dict(unpack(raw))
        except Exception:
            return {}

    def get_status(self):
        try:
            return unpack(self._props.Get(PLAYER_IFACE, "Status"))
        except Exception:
            return "stopped"

    def play(self):
        try:
            self._player.Play()
        except Exception as e:
            log.warning("Play: %s", e)

    def pause(self):
        try:
            self._player.Pause()
        except Exception as e:
            log.warning("Pause: %s", e)

    def next_track(self):
        try:
            self._player.Next()
        except Exception as e:
            log.warning("Next: %s", e)

    def previous_track(self):
        try:
            self._player.Previous()
        except Exception as e:
            log.warning("Previous: %s", e)
