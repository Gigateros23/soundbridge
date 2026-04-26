from gi.repository import GLib


def unpack(v):
    if isinstance(v, GLib.Variant):
        return v.unpack()
    return v


def unpack_props(props):
    return {k: unpack(v) for k, v in props.items()}
