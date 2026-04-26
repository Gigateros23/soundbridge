import subprocess
import logging

log = logging.getLogger(__name__)
_loopback_modules = {}  # mac_address -> module_id


def _pactl(*args):
    try:
        return subprocess.check_output(["pactl"] + list(args), text=True).strip()
    except Exception as e:
        log.warning("pactl %s: %s", args[0], e)
        return ""


def get_sinks():
    """Return list of (name, description) for available output sinks."""
    sinks = []
    name = None
    for line in _pactl("list", "sinks").splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Description:") and name:
            desc = line.split(":", 1)[1].strip()
            if not name.startswith("bluez_output"):
                sinks.append((name, desc))
            name = None
    return sinks


def get_default_sink():
    return _pactl("get-default-sink")


def set_default_sink(sink_name):
    _pactl("set-default-sink", sink_name)


def _find_bt_source(mac_address):
    mac = mac_address.replace(":", "_")
    for line in _pactl("list", "sources", "short").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and mac.lower() in parts[1].lower() and "monitor" not in parts[1]:
            return parts[1]
    return None


def route_device(mac_address, sink_name):
    """Route a Bluetooth device's audio stream to a specific sink."""
    unroute_device(mac_address)
    source = _find_bt_source(mac_address)
    if not source:
        log.warning("No BT source found for %s — falling back to default sink", mac_address)
        set_default_sink(sink_name)
        return
    result = _pactl(
        "load-module", "module-loopback",
        f"source={source}", f"sink={sink_name}", "latency_msec=100"
    )
    if result.isdigit():
        _loopback_modules[mac_address] = int(result)
        log.info("Routed %s → %s (module %s)", mac_address, sink_name, result)
    else:
        set_default_sink(sink_name)


def unroute_device(mac_address):
    module_id = _loopback_modules.pop(mac_address, None)
    if module_id:
        _pactl("unload-module", str(module_id))
        log.info("Unrouted %s", mac_address)
