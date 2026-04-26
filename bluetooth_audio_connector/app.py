import subprocess
import logging
from gi.repository import GLib
from .bluetooth import BluetoothManager
from .window import MainWindow
from .tray import TrayIcon
from . import notifications, audio, settings
from .mpris import MPRISService

log = logging.getLogger(__name__)


class App:
    def __init__(self):
        self._settings = settings.load()
        self._loop = GLib.MainLoop()
        self._current_player = None

        self._bt = BluetoothManager()
        self._bt.on_devices_changed = self._refresh
        self._bt.on_device_connected = self._on_connected
        self._bt.on_device_disconnected = self._on_disconnected
        self._bt.on_player_added = self._on_player_added

        callbacks = {
            "connect": self._bt.connect,
            "disconnect": self._bt.disconnect,
            "play": self._play,
            "pause": self._pause,
            "next": self._next,
            "previous": self._previous,
            "set_sink": self._set_sink,
            "open_settings": self._open_bt_settings,
            "set_auto_reconnect": self._set_auto_reconnect,
            "raise_window": lambda: self._window.toggle() if not self._window.get_visible() else None,
        }

        self._mpris = MPRISService(callbacks)
        self._window = MainWindow(callbacks)
        self._tray = TrayIcon(
            on_toggle_window=self._window.toggle,
            on_open_settings=self._open_bt_settings,
            on_exit=self._exit,
        )

    def run(self):
        self._refresh()
        self._window.update_sinks(
            audio.get_sinks(),
            active=self._settings.get("last_sink"),
        )
        self._window.update_settings(self._settings.get("auto_reconnect", False))

        if self._settings.get("auto_reconnect") and self._settings.get("last_devices"):
            GLib.timeout_add(3000, self._auto_reconnect)

        self._loop.run()

    # ── Device events ─────────────────────────────────────────────────────

    def _refresh(self):
        devices = self._bt.get_all_devices()
        self._window.update_devices(devices)
        self._tray.update(devices)

    def _on_connected(self, device):
        notifications.device_connected(device.name)
        log.info("Device connected: %s (supports_audio=%s)", device.name, device.supports_audio)
        if not device.supports_audio:
            return
        # Delay routing — BT audio source appears in PipeWire a few seconds after connection
        sink_pref = self._settings.get("sink_preferences", {}).get(device.address)
        if sink_pref:
            GLib.timeout_add(3000, lambda: audio.route_device(device.address, sink_pref) or False)
        GLib.timeout_add(1500, lambda: self._init_avrcp(device.path))

    def _init_avrcp(self, device_path):
        self._bt.connect_avrcp(device_path)
        self._try_attach_player(device_path, retries=6)
        return False

    def _try_attach_player(self, device_path, retries=6):
        player = self._bt.get_player(device_path)
        if player:
            self._attach_player(player)
            return
        if retries > 0:
            GLib.timeout_add(2000, lambda: self._try_attach_player(device_path, retries - 1))
        else:
            log.warning("AVRCP player not found for %s after retries", device_path)

    def _on_disconnected(self, device):
        notifications.device_disconnected(device.name)
        audio.unroute_device(device.address)
        if self._current_player:
            self._current_player = None
            self._window.update_track({}, "stopped")
            self._mpris.clear()

    def _on_player_added(self, device_path, player):
        device = next((d for d in self._bt.get_all_devices() if d.path == device_path), None)
        name = device.name if device else device_path
        log.info("AVRCP player ready for %s (supports_audio=%s)", name, device.supports_audio if device else "?")
        # MediaPlayer1 only exists on audio/media devices — always attach
        self._attach_player(player)

    def _attach_player(self, player):
        self._current_player = player

        def on_track(track):
            status = self._current_player.get_status()
            GLib.idle_add(self._window.update_track, track, status)
            GLib.idle_add(self._mpris.update, track, status)

        def on_status(status):
            track = self._current_player.get_track()
            GLib.idle_add(self._window.update_track, track, status)
            GLib.idle_add(self._mpris.update, track, status)

        player.on_track_changed = on_track
        player.on_status_changed = on_status

        track = player.get_track()
        status = player.get_status()
        self._window.update_track(track, status)
        self._mpris.update(track, status)

    # ── AVRCP controls ────────────────────────────────────────────────────

    def _play(self):
        if self._current_player:
            self._current_player.play()

    def _pause(self):
        if self._current_player:
            self._current_player.pause()

    def _next(self):
        if self._current_player:
            self._current_player.next_track()

    def _previous(self):
        if self._current_player:
            self._current_player.previous_track()

    # ── Audio output ──────────────────────────────────────────────────────

    def _set_sink(self, sink_name):
        self._settings["last_sink"] = sink_name
        prefs = self._settings.setdefault("sink_preferences", {})
        for device in self._bt.get_audio_devices():
            if device.connected:
                audio.route_device(device.address, sink_name)
                prefs[device.address] = sink_name
        settings.save(self._settings)

    # ── Settings ──────────────────────────────────────────────────────────

    def _set_auto_reconnect(self, value):
        self._settings["auto_reconnect"] = value
        settings.save(self._settings)

    def _auto_reconnect(self):
        for path in self._settings.get("last_devices", []):
            log.info("Auto-reconnecting %s", path)
            self._bt.connect(path)
        return False

    # ── Misc ──────────────────────────────────────────────────────────────

    def _open_bt_settings(self):
        for cmd in [
            ["gnome-control-center", "bluetooth"],
            ["systemsettings5", "kcm_bluetooth"],
            ["blueman-manager"],
            ["bluedevil-wizard"],
        ]:
            try:
                subprocess.Popen(cmd)
                return
            except FileNotFoundError:
                continue
        log.warning("No Bluetooth settings app found")

    def _exit(self):
        connected = [d for d in self._bt.get_all_devices() if d.connected]
        self._settings["last_devices"] = [d.path for d in connected]
        settings.save(self._settings)
        self._loop.quit()
