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
    def __init__(self, on_toggle_window, on_open_settings, on_exit):
        self._on_toggle = on_toggle_window
        self._on_settings = on_open_settings
        self._on_exit = on_exit

        self._indicator = AppIndicator.Indicator.new(
            "soundbridge",
            ICON_DEFAULT,
            AppIndicator.IndicatorCategory.HARDWARE,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_title("soundbridge")
        self._indicator.set_menu(self._build_menu())

    def _build_menu(self):
        menu = Gtk.Menu()

        open_item = Gtk.MenuItem(label="Open soundbridge")
        open_item.connect("activate", lambda _: self._on_toggle())
        menu.append(open_item)

        menu.append(Gtk.SeparatorMenuItem())

        settings_item = Gtk.MenuItem(label="Bluetooth Settings")
        settings_item.connect("activate", lambda _: self._on_settings())
        menu.append(settings_item)

        exit_item = Gtk.MenuItem(label="Exit")
        exit_item.connect("activate", lambda _: self._on_exit())
        menu.append(exit_item)

        menu.show_all()
        return menu

    def update(self, devices):
        audio_devices = [d for d in devices if d.supports_audio]
        connected = any(d.connected for d in audio_devices)
        self._indicator.set_icon_full(
            ICON_CONNECTED if connected else ICON_DEFAULT,
            "soundbridge",
        )
