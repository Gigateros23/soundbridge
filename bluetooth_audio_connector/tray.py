import subprocess
import gi
gi.require_version("Gtk", "3.0")

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except (ValueError, ImportError):
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppIndicator

from gi.repository import Gtk

ICON_DEFAULT = "bluetooth"
ICON_CONNECTED = "bluetooth-active"


class TrayIcon:
    def __init__(self, on_connect, on_disconnect, on_open_settings, on_exit):
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_open_settings = on_open_settings
        self._on_exit = on_exit

        self._indicator = AppIndicator.Indicator.new(
            "soundbridge",
            ICON_DEFAULT,
            AppIndicator.IndicatorCategory.HARDWARE,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_title("soundbridge")

        self._menu = Gtk.Menu()
        self._indicator.set_menu(self._menu)

    def update(self, devices):
        for child in self._menu.get_children():
            self._menu.remove(child)

        audio_devices = [d for d in devices if d.supports_audio]

        if audio_devices:
            for device in audio_devices:
                label = ("✓  " if device.connected else "      ") + device.name
                item = Gtk.MenuItem(label=label)
                if device.connected:
                    item.connect("activate", lambda _w, d=device: self._on_disconnect(d.path))
                else:
                    item.connect("activate", lambda _w, d=device: self._on_connect(d.path))
                self._menu.append(item)
        else:
            placeholder = Gtk.MenuItem(label="No audio devices paired")
            placeholder.set_sensitive(False)
            self._menu.append(placeholder)

        self._menu.append(Gtk.SeparatorMenuItem())

        settings_item = Gtk.MenuItem(label="Bluetooth Settings")
        settings_item.connect("activate", lambda _: self._on_open_settings())
        self._menu.append(settings_item)

        exit_item = Gtk.MenuItem(label="Exit")
        exit_item.connect("activate", lambda _: self._on_exit())
        self._menu.append(exit_item)

        self._menu.show_all()

        any_connected = any(d.connected for d in audio_devices)
        self._indicator.set_icon_full(
            ICON_CONNECTED if any_connected else ICON_DEFAULT,
            "soundbridge",
        )
