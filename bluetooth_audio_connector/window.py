import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango

_CSS = b"""
.section-label {
    font-size: 0.75rem;
    font-weight: bold;
    color: alpha(@theme_fg_color, 0.55);
    letter-spacing: 1px;
}
.now-playing-box {
    background-color: alpha(@theme_selected_bg_color, 0.08);
    border-radius: 8px;
    padding: 12px;
}
.track-title {
    font-size: 1.05rem;
    font-weight: bold;
}
.track-artist {
    font-size: 0.9rem;
}
.device-list {
    border-radius: 6px;
}
"""


def _load_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def _section_label(text):
    label = Gtk.Label(label=text)
    label.set_halign(Gtk.Align.START)
    label.get_style_context().add_class("section-label")
    return label


def _spacer(px=8):
    box = Gtk.Box()
    box.set_size_request(-1, px)
    return box


class MainWindow(Gtk.Window):
    def __init__(self, callbacks):
        super().__init__()
        self._cb = callbacks
        self._is_playing = False
        _load_css()
        self._build()
        self.connect("delete-event", lambda *_: self.hide() or True)

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build(self):
        self.set_title("soundbridge")
        self.set_default_size(360, 520)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("soundbridge")
        header.set_subtitle("Bluetooth Audio Receiver")
        self.set_titlebar(header)

        bt_btn = Gtk.Button()
        bt_btn.set_image(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.BUTTON))
        bt_btn.set_tooltip_text("Bluetooth Settings")
        bt_btn.connect("clicked", lambda _: self._cb["open_settings"]())
        header.pack_end(bt_btn)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_margin_start(16)
        root.set_margin_end(16)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        self.add(root)

        root.pack_start(_section_label("DEVICES"), False, False, 0)
        root.pack_start(_spacer(6), False, False, 0)
        root.pack_start(self._build_device_list(), False, False, 0)

        root.pack_start(_spacer(16), False, False, 0)
        root.pack_start(_section_label("NOW PLAYING"), False, False, 0)
        root.pack_start(_spacer(6), False, False, 0)
        root.pack_start(self._build_now_playing(), False, False, 0)

        root.pack_start(_spacer(16), False, False, 0)
        root.pack_start(_section_label("AUDIO OUTPUT"), False, False, 0)
        root.pack_start(_spacer(6), False, False, 0)
        root.pack_start(self._build_sink_selector(), False, False, 0)

        root.pack_start(_spacer(16), False, False, 0)
        root.pack_start(Gtk.Separator(), False, False, 0)
        root.pack_start(_spacer(12), False, False, 0)
        root.pack_start(self._build_footer(), False, False, 0)

    def _build_device_list(self):
        self._device_listbox = Gtk.ListBox()
        self._device_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._device_listbox.get_style_context().add_class("frame")
        self._device_listbox.get_style_context().add_class("device-list")
        return self._device_listbox

    def _build_now_playing(self):
        self._np_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._np_box.get_style_context().add_class("now-playing-box")

        self._track_title = Gtk.Label(label="Nothing playing")
        self._track_title.set_halign(Gtk.Align.START)
        self._track_title.set_ellipsize(Pango.EllipsizeMode.END)
        self._track_title.get_style_context().add_class("track-title")
        self._np_box.pack_start(self._track_title, False, False, 0)

        self._track_artist = Gtk.Label(label="")
        self._track_artist.set_halign(Gtk.Align.START)
        self._track_artist.set_ellipsize(Pango.EllipsizeMode.END)
        self._track_artist.get_style_context().add_class("track-artist")
        self._track_artist.get_style_context().add_class("dim-label")
        self._np_box.pack_start(self._track_artist, False, False, 0)

        controls = Gtk.Box(spacing=4)
        controls.set_halign(Gtk.Align.CENTER)
        controls.set_margin_top(6)

        self._prev_btn = self._media_button("media-skip-backward-symbolic", lambda _: self._cb["previous"]())
        self._play_btn = self._media_button("media-playback-start-symbolic", self._on_play_clicked, large=True)
        self._next_btn = self._media_button("media-skip-forward-symbolic", lambda _: self._cb["next"]())

        controls.pack_start(self._prev_btn, False, False, 0)
        controls.pack_start(self._play_btn, False, False, 0)
        controls.pack_start(self._next_btn, False, False, 0)
        self._np_box.pack_start(controls, False, False, 0)

        return self._np_box

    def _media_button(self, icon_name, handler, large=False):
        size = Gtk.IconSize.LARGE_TOOLBAR if large else Gtk.IconSize.BUTTON
        btn = Gtk.Button()
        btn.set_image(Gtk.Image.new_from_icon_name(icon_name, size))
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", handler)
        return btn

    def _build_sink_selector(self):
        self._sink_combo = Gtk.ComboBoxText()
        self._sink_combo_handler = self._sink_combo.connect("changed", self._on_sink_changed)
        return self._sink_combo

    def _build_footer(self):
        box = Gtk.Box(spacing=8)

        self._auto_reconnect_check = Gtk.CheckButton(label="Auto-reconnect on startup")
        self._auto_reconnect_check.connect("toggled", lambda w: self._cb["set_auto_reconnect"](w.get_active()))
        box.pack_start(self._auto_reconnect_check, True, True, 0)

        pair_btn = Gtk.Button(label="Pair device")
        pair_btn.connect("clicked", lambda _: self._cb["open_settings"]())
        box.pack_start(pair_btn, False, False, 0)

        return box

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_play_clicked(self, _):
        if self._is_playing:
            self._cb["pause"]()
        else:
            self._cb["play"]()

    def _on_sink_changed(self, combo):
        sink = combo.get_active_id()
        if sink:
            self._cb["set_sink"](sink)

    # ── Public update methods ──────────────────────────────────────────────

    def update_devices(self, devices):
        for row in self._device_listbox.get_children():
            self._device_listbox.remove(row)

        audio_devices = [d for d in devices if d.supports_audio]

        if not audio_devices:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label="No paired audio devices")
            lbl.set_margin_top(18)
            lbl.set_margin_bottom(18)
            lbl.get_style_context().add_class("dim-label")
            row.add(lbl)
            self._device_listbox.add(row)
        else:
            for d in audio_devices:
                self._device_listbox.add(self._make_device_row(d))

        self._device_listbox.show_all()

    def _make_device_row(self, device):
        row = Gtk.ListBoxRow()

        box = Gtk.Box(spacing=10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        icon = Gtk.Image.new_from_icon_name("audio-headphones-symbolic", Gtk.IconSize.BUTTON)
        box.pack_start(icon, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_lbl = Gtk.Label()
        name_lbl.set_markup(f"<b>{GLib.markup_escape_text(device.name)}</b>")
        name_lbl.set_halign(Gtk.Align.START)
        info.pack_start(name_lbl, False, False, 0)

        if device.connected:
            status_lbl = Gtk.Label(label="● Connected")
            status_lbl.set_halign(Gtk.Align.START)
            status_lbl.get_style_context().add_class("dim-label")
            info.pack_start(status_lbl, False, False, 0)

        box.pack_start(info, True, True, 0)

        if device.connected:
            btn = Gtk.Button(label="Disconnect")
            btn.get_style_context().add_class("destructive-action")
            btn.connect("clicked", lambda _, p=device.path: self._cb["disconnect"](p))
        else:
            btn = Gtk.Button(label="Connect")
            btn.get_style_context().add_class("suggested-action")
            btn.connect("clicked", lambda _, p=device.path: self._cb["connect"](p))

        box.pack_start(btn, False, False, 0)
        row.add(box)
        return row

    def update_track(self, track, status):
        title = track.get("Title", "")
        artist = track.get("Artist", "")
        album = track.get("Album", "")

        if title:
            self._track_title.set_text(title)
            subtitle = " — ".join(filter(None, [artist, album]))
            self._track_artist.set_text(subtitle)
        else:
            self._track_title.set_text("Nothing playing")
            self._track_artist.set_text("")

        self._is_playing = status == "playing"
        icon = "media-playback-pause-symbolic" if self._is_playing else "media-playback-start-symbolic"
        self._play_btn.set_image(
            Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        )
        self._play_btn.show_all()

    def update_sinks(self, sinks, active=None):
        self._sink_combo.handler_block(self._sink_combo_handler)
        self._sink_combo.remove_all()
        for name, desc in sinks:
            self._sink_combo.append(name, desc)
        if active:
            self._sink_combo.set_active_id(active)
        elif sinks:
            self._sink_combo.set_active(0)
        self._sink_combo.handler_unblock(self._sink_combo_handler)

    def update_settings(self, auto_reconnect):
        self._auto_reconnect_check.set_active(auto_reconnect)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            self.present()
