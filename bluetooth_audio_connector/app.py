import subprocess
import logging
from gi.repository import GLib
from .bluetooth import BluetoothManager
from .tray import TrayIcon
from . import settings

log = logging.getLogger(__name__)


class App:
    def __init__(self):
        self._settings = settings.load()
        self._loop = GLib.MainLoop()

        self._bt = BluetoothManager()
        self._bt.on_devices_changed = self._refresh_tray

        self._tray = TrayIcon(
            on_connect=self._connect,
            on_disconnect=self._disconnect,
            on_open_settings=self._open_bt_settings,
            on_exit=self._exit,
        )

    def run(self):
        self._refresh_tray()
        if self._settings.get("auto_reconnect") and self._settings.get("last_devices"):
            GLib.timeout_add(3000, self._auto_reconnect)
        self._loop.run()

    def _refresh_tray(self):
        self._tray.update(self._bt.get_all_devices())

    def _connect(self, path):
        self._bt.connect(path)

    def _disconnect(self, path):
        self._bt.disconnect(path)
        if path in self._settings["last_devices"]:
            self._settings["last_devices"].remove(path)
            settings.save(self._settings)

    def _auto_reconnect(self):
        for path in self._settings["last_devices"]:
            log.info("Auto-reconnecting %s", path)
            self._bt.connect(path)
        return False

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
        self._settings["auto_reconnect"] = bool(connected)
        settings.save(self._settings)
        self._loop.quit()
