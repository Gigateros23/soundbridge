import logging
from gi.repository import GLib
from dasbus.connection import SystemMessageBus

A2DP_SOURCE_UUID = "0000110a-0000-1000-8000-00805f9b34fb"

log = logging.getLogger(__name__)


def _unpack(v):
    if isinstance(v, GLib.Variant):
        return v.unpack()
    return v


def _unpack_props(props):
    return {k: _unpack(v) for k, v in props.items()}


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
        self._devices = {}
        self._prop_proxies = {}
        self.on_devices_changed = None

        self._manager = self._bus.get_proxy(
            "org.bluez", "/",
            "org.freedesktop.DBus.ObjectManager"
        )
        self._load_existing_devices()
        self._manager.InterfacesAdded.connect(self._on_interfaces_added)
        self._manager.InterfacesRemoved.connect(self._on_interfaces_removed)

    def _load_existing_devices(self):
        try:
            objects = self._manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if "org.bluez.Device1" in interfaces:
                    props = _unpack_props(interfaces["org.bluez.Device1"])
                    self._register_device(path, props)
        except Exception as e:
            log.error("Failed to load devices: %s", e)

    def _register_device(self, path, props):
        device = BluetoothDevice(path, props)
        self._devices[path] = device
        proxy = self._bus.get_proxy("org.bluez", path, "org.freedesktop.DBus.Properties")
        proxy.PropertiesChanged.connect(
            lambda iface, changed, _inv: self._on_props_changed(path, iface, changed)
        )
        self._prop_proxies[path] = proxy

    def _on_interfaces_added(self, path, interfaces):
        if "org.bluez.Device1" not in interfaces:
            return
        props = _unpack_props(interfaces["org.bluez.Device1"])
        self._register_device(path, props)
        self._notify()

    def _on_interfaces_removed(self, path, interfaces):
        if "org.bluez.Device1" not in interfaces or path not in self._devices:
            return
        del self._devices[path]
        self._prop_proxies.pop(path, None)
        self._notify()

    def _on_props_changed(self, path, iface, changed):
        if iface != "org.bluez.Device1" or path not in self._devices:
            return
        device = self._devices[path]
        changed = _unpack_props(changed)
        if "Connected" in changed:
            device.connected = bool(changed["Connected"])
        if "Name" in changed:
            device.name = changed["Name"]
        if "UUIDs" in changed:
            device.uuids = [u.lower() for u in changed["UUIDs"]]
        self._notify()

    def _notify(self):
        if self.on_devices_changed:
            GLib.idle_add(self.on_devices_changed)

    def get_audio_devices(self):
        return [d for d in self._devices.values() if d.supports_audio]

    def get_all_devices(self):
        return list(self._devices.values())

    def connect(self, path):
        try:
            proxy = self._bus.get_proxy("org.bluez", path, "org.bluez.Device1")
            proxy.Connect()
            log.info("Connected to %s", path)
        except Exception as e:
            log.error("Connect failed for %s: %s", path, e)

    def disconnect(self, path):
        try:
            proxy = self._bus.get_proxy("org.bluez", path, "org.bluez.Device1")
            proxy.Disconnect()
            log.info("Disconnected from %s", path)
        except Exception as e:
            log.error("Disconnect failed for %s: %s", path, e)
