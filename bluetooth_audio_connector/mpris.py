import logging
from gi.repository import Gio, GLib

log = logging.getLogger(__name__)

_BUS_NAME = "org.mpris.MediaPlayer2.soundbridge"
_OBJ_PATH = "/org/mpris/MediaPlayer2"

_XML = """
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <property name="CanQuit"             type="b"  access="read"/>
    <property name="CanRaise"            type="b"  access="read"/>
    <property name="HasTrackList"        type="b"  access="read"/>
    <property name="Identity"            type="s"  access="read"/>
    <property name="DesktopEntry"        type="s"  access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes"  type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/>
    <method name="Previous"/>
    <method name="Pause"/>
    <method name="PlayPause"/>
    <method name="Stop"/>
    <method name="Play"/>
    <method name="Seek">
      <arg direction="in" type="x" name="Offset"/>
    </method>
    <method name="SetPosition">
      <arg direction="in" type="o" name="TrackId"/>
      <arg direction="in" type="x" name="Position"/>
    </method>
    <method name="OpenUri">
      <arg direction="in" type="s" name="Uri"/>
    </method>
    <signal name="Seeked">
      <arg type="x" name="Position"/>
    </signal>
    <property name="PlaybackStatus" type="s"    access="read"/>
    <property name="LoopStatus"     type="s"    access="readwrite"/>
    <property name="Rate"           type="d"    access="readwrite"/>
    <property name="Shuffle"        type="b"    access="readwrite"/>
    <property name="Metadata"       type="a{sv}" access="read"/>
    <property name="Volume"         type="d"    access="readwrite"/>
    <property name="Position"       type="x"    access="read"/>
    <property name="MinimumRate"    type="d"    access="read"/>
    <property name="MaximumRate"    type="d"    access="read"/>
    <property name="CanGoNext"      type="b"    access="read"/>
    <property name="CanGoPrevious"  type="b"    access="read"/>
    <property name="CanPlay"        type="b"    access="read"/>
    <property name="CanPause"       type="b"    access="read"/>
    <property name="CanSeek"        type="b"    access="read"/>
    <property name="CanControl"     type="b"    access="read"/>
  </interface>
</node>
"""


class MPRISService:
    def __init__(self, callbacks):
        self._cb = callbacks
        self._track = {}
        self._status = "stopped"
        self._conn = None
        self._node = Gio.DBusNodeInfo.new_for_xml(_XML)

        Gio.bus_own_name(
            Gio.BusType.SESSION,
            _BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            lambda *_: log.info("MPRIS2 service active"),
            lambda *_: log.warning("Failed to acquire MPRIS2 bus name"),
        )

    def _on_bus_acquired(self, conn, name):
        self._conn = conn
        for iface in self._node.interfaces:
            conn.register_object(
                _OBJ_PATH, iface,
                self._on_method, self._on_get, self._on_set,
            )

    # ── Incoming calls from GNOME / media keys ────────────────────────────

    def _on_method(self, conn, sender, path, iface, method, params, inv):
        match method:
            case "Play":
                self._cb.get("play", lambda: None)()
            case "Pause":
                self._cb.get("pause", lambda: None)()
            case "PlayPause":
                if self._status == "playing":
                    self._cb.get("pause", lambda: None)()
                else:
                    self._cb.get("play", lambda: None)()
            case "Next":
                self._cb.get("next", lambda: None)()
            case "Previous":
                self._cb.get("previous", lambda: None)()
            case "Raise":
                self._cb.get("raise_window", lambda: None)()
        inv.return_value(None)

    def _on_get(self, conn, sender, path, iface, prop):
        if iface == "org.mpris.MediaPlayer2":
            return self._root_prop(prop)
        if iface == "org.mpris.MediaPlayer2.Player":
            return self._player_prop(prop)
        return None

    def _on_set(self, *_):
        return False

    def _root_prop(self, name):
        match name:
            case "CanQuit":             return GLib.Variant("b", False)
            case "CanRaise":            return GLib.Variant("b", True)
            case "HasTrackList":        return GLib.Variant("b", False)
            case "Identity":            return GLib.Variant("s", "soundbridge")
            case "DesktopEntry":        return GLib.Variant("s", "soundbridge")
            case "SupportedUriSchemes": return GLib.Variant("as", [])
            case "SupportedMimeTypes":  return GLib.Variant("as", [])
        return None

    def _player_prop(self, name):
        active = bool(self._track)
        status = self._status.capitalize() if self._status else "Stopped"
        match name:
            case "PlaybackStatus": return GLib.Variant("s", status)
            case "LoopStatus":     return GLib.Variant("s", "None")
            case "Rate":           return GLib.Variant("d", 1.0)
            case "Shuffle":        return GLib.Variant("b", False)
            case "Metadata":       return GLib.Variant("a{sv}", self._metadata())
            case "Volume":         return GLib.Variant("d", 1.0)
            case "Position":       return GLib.Variant("x", 0)
            case "MinimumRate":    return GLib.Variant("d", 1.0)
            case "MaximumRate":    return GLib.Variant("d", 1.0)
            case "CanGoNext":      return GLib.Variant("b", active)
            case "CanGoPrevious":  return GLib.Variant("b", active)
            case "CanPlay":        return GLib.Variant("b", active)
            case "CanPause":       return GLib.Variant("b", active)
            case "CanSeek":        return GLib.Variant("b", False)
            case "CanControl":     return GLib.Variant("b", active)
        return None

    def _metadata(self):
        t = self._track
        meta = {"mpris:trackid": GLib.Variant("o", "/org/soundbridge/track/0")}
        if t.get("Title"):
            meta["xesam:title"] = GLib.Variant("s", t["Title"])
        if t.get("Artist"):
            meta["xesam:artist"] = GLib.Variant("as", [t["Artist"]])
        if t.get("Album"):
            meta["xesam:album"] = GLib.Variant("s", t["Album"])
        if t.get("Duration"):
            meta["mpris:length"] = GLib.Variant("x", int(t["Duration"]) * 1000)
        return meta

    # ── Called when AVRCP sends an update ────────────────────────────────

    def update(self, track, status):
        self._track = track or {}
        self._status = status or "stopped"
        active = bool(self._track)
        self._emit({
            "PlaybackStatus": GLib.Variant("s", self._status.capitalize()),
            "Metadata":       GLib.Variant("a{sv}", self._metadata()),
            "CanPlay":        GLib.Variant("b", active),
            "CanPause":       GLib.Variant("b", active),
            "CanGoNext":      GLib.Variant("b", active),
            "CanGoPrevious":  GLib.Variant("b", active),
            "CanControl":     GLib.Variant("b", active),
        })

    def clear(self):
        self._track = {}
        self._status = "stopped"
        self.update({}, "stopped")

    def _emit(self, changed):
        if not self._conn:
            return
        try:
            self._conn.emit_signal(
                None, _OBJ_PATH,
                "org.freedesktop.DBus.Properties",
                "PropertiesChanged",
                GLib.Variant("(sa{sv}as)", [
                    "org.mpris.MediaPlayer2.Player",
                    changed,
                    [],
                ]),
            )
        except Exception as e:
            log.warning("MPRIS emit error: %s", e)
