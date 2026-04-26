import logging
from gi.repository import GLib
from dasbus.connection import SystemMessageBus
from ._utils import unpack, unpack_props
from .avrcp import AVRCPPlayer

BLUEZ = "org.bluez"
DEVICE_IFACE = "org.bluez.Device1"
PLAYER_IFACE = "org.bluez.MediaPlayer1"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
A2DP_SOURCE_UUID = "0000110a-0000-1000-8000-00805f9b34fb"
AVRCP_CONTROLLER_UUID = "0000110f-0000-1000-8000-00805f9b34fb"

log = logging.getLogger(__name__)


class BluetoothDevice:
    def __init__(self, path, props):
        self.path = path
        self.name = props.get("Name", "Unknown")
        self.address = props.get("Address", "")
        self.connected = bool(props.get("Connected", False))
        self.uuids = [u.lower() for u in props.get("UUIDs", [])]

    @property
    def supports_audio(self):
        return A2DP_SOURCE_UUID in self.uuids


class BluetoothManager:
    def __init__(self):
        self._bus = SystemMessageBus()
        self._devices = {}       # path -> BluetoothDevice
        self._prop_proxies = {}  # path -> Properties proxy
        self._players = {}       # device_path -> AVRCPPlayer

        self.on_devices_changed = None
        self.on_device_connected = None
        self.on_device_disconnected = None
        self.on_player_added = None

        self._manager = self._bus.get_proxy(BLUEZ, "/", "org.freedesktop.DBus.ObjectManager")
        self._load_existing()
        self._manager.InterfacesAdded.connect(self._on_interfaces_added)
        self._manager.InterfacesRemoved.connect(self._on_interfaces_removed)

    # ── Init ──────────────────────────────────────────────────────────────

    def _load_existing(self):
        try:
            for path, interfaces in self._manager.GetManagedObjects().items():
                if DEVICE_IFACE in interfaces:
                    props = unpack_props(interfaces[DEVICE_IFACE])
                    self._register_device(path, props)
                if PLAYER_IFACE in interfaces:
                    self._register_player(path)
        except Exception as e:
            log.error("Failed to load objects: %s", e)

    def _register_device(self, path, props):
        device = BluetoothDevice(path, props)
        self._devices[path] = device
        proxy = self._bus.get_proxy(BLUEZ, path, PROPS_IFACE)
        proxy.PropertiesChanged.connect(
            lambda iface, changed, _inv: self._on_props_changed(path, iface, changed)
        )
        self._prop_proxies[path] = proxy

    def _register_player(self, player_path):
        device_path = "/".join(player_path.split("/")[:-1])
        try:
            player = AVRCPPlayer(self._bus, player_path)
            self._players[device_path] = player
            log.info("AVRCP player registered for %s", device_path)
            if self.on_player_added:
                GLib.idle_add(self.on_player_added, device_path, player)
        except Exception as e:
            log.warning("Failed to register player %s: %s", player_path, e)

    # ── D-Bus signals ──────────────────────────────────────────────────────

    def _on_interfaces_added(self, path, interfaces):
        if DEVICE_IFACE in interfaces:
            props = unpack_props(interfaces[DEVICE_IFACE])
            self._register_device(path, props)
            self._notify()
        if PLAYER_IFACE in interfaces:
            self._register_player(path)

    def _on_interfaces_removed(self, path, interfaces):
        if DEVICE_IFACE in interfaces and path in self._devices:
            del self._devices[path]
            self._prop_proxies.pop(path, None)
            self._players.pop(path, None)
            self._notify()
        if PLAYER_IFACE in interfaces:
            device_path = "/".join(path.split("/")[:-1])
            self._players.pop(device_path, None)

    def _on_props_changed(self, path, iface, changed):
        if iface != DEVICE_IFACE or path not in self._devices:
            return
        device = self._devices[path]
        changed = unpack_props(changed)

        was_connected = device.connected
        if "Connected" in changed:
            device.connected = bool(changed["Connected"])
        if "Name" in changed:
            device.name = changed["Name"]
        if "UUIDs" in changed:
            device.uuids = [u.lower() for u in changed["UUIDs"]]

        if not was_connected and device.connected and self.on_device_connected:
            GLib.idle_add(self.on_device_connected, device)
        elif was_connected and not device.connected and self.on_device_disconnected:
            GLib.idle_add(self.on_device_disconnected, device)

        self._notify()

    def _notify(self):
        if self.on_devices_changed:
            GLib.idle_add(self.on_devices_changed)

    # ── Public API ─────────────────────────────────────────────────────────

    def get_all_devices(self):
        return list(self._devices.values())

    def get_audio_devices(self):
        return [d for d in self._devices.values() if d.supports_audio]

    def get_player(self, device_path):
        return self._players.get(device_path)

    def connect(self, path):
        try:
            self._bus.get_proxy(BLUEZ, path, DEVICE_IFACE).Connect()
        except Exception as e:
            log.error("Connect %s: %s", path, e)

    def connect_avrcp(self, path):
        try:
            self._bus.get_proxy(BLUEZ, path, DEVICE_IFACE).ConnectProfile(AVRCP_CONTROLLER_UUID)
            log.info("AVRCP connected for %s", path)
        except Exception as e:
            log.warning("AVRCP connect failed for %s: %s", path, e)

    def disconnect(self, path):
        try:
            self._bus.get_proxy(BLUEZ, path, DEVICE_IFACE).Disconnect()
        except Exception as e:
            log.error("Disconnect %s: %s", path, e)
