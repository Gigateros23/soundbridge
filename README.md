# soundbridge 🔊

Stream audio from your phone to your Linux PC over Bluetooth — no cables, no apps, just sound.

Your PC becomes a Bluetooth speaker. Pair your phone once, click to connect, and hear your phone's audio through your computer's speakers.

---

## Features

- System tray icon — one click to connect or disconnect
- Auto-reconnect on startup to your last device
- Works with any phone that supports Bluetooth A2DP (Android & iOS)
- Light/dark icon follows your desktop theme
- Quick access to Bluetooth Settings
- Compatible with GNOME, KDE, XFCE and other desktops

---

## Requirements

| Component | Purpose |
|-----------|---------|
| BlueZ | Linux Bluetooth stack |
| PipeWire + WirePlumber **or** PulseAudio | Audio routing |
| Python 3.10+ | Runtime |
| python-gobject | GTK bindings |
| libayatana-appindicator | System tray |
| dasbus | D-Bus / BlueZ interface |

---

## Installation

### Arch Linux / CachyOS / Manjaro

```bash
git clone https://github.com/yourusername/soundbridge.git
cd soundbridge
bash setup.sh
```

### Ubuntu / Debian / Pop!_OS

```bash
sudo apt install -y python3-gi python3-gi-cairo \
    gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
    python3-dasbus bluez pulseaudio-module-bluetooth

git clone https://github.com/yourusername/soundbridge.git
cd soundbridge
bash setup.sh
```

### Fedora

```bash
sudo dnf install -y python3-gobject python3-dasbus \
    libayatana-appindicator-gtk3 bluez

git clone https://github.com/yourusername/soundbridge.git
cd soundbridge
bash setup.sh
```

---

## First-time setup: pairing your phone

Open a terminal and run:

```bash
bluetoothctl
```

Then type these commands one by one:

```
power on
discoverable on
pairable on
scan on
```

On your phone, go to **Bluetooth Settings** and select your PC from the list.
Accept the pairing request on both sides.

Once paired, open soundbridge from the system tray and click your phone's name to connect.
On your phone, make sure **Media Audio** is enabled for the connection.

---

## Usage

```bash
soundbridge
```

The icon appears in your system tray.

| Action | Result |
|--------|--------|
| Click icon → tap a device | Connect (phone audio plays on PC) |
| Click icon → tap a connected device | Disconnect |
| Right-click → Bluetooth Settings | Open system Bluetooth panel |
| Right-click → Exit | Quit (remembers connected devices for next start) |

On next launch, soundbridge automatically reconnects to any device that was connected when you exited.

---

## How it works

soundbridge uses the **Bluetooth A2DP Sink** profile. Normally, a phone acts as a source (speaker output) and a Bluetooth speaker is the sink (receives audio). soundbridge makes your Linux PC act as the sink — so your phone streams audio to your PC just like it would to a wireless speaker.

Technically:

1. WirePlumber (or PulseAudio) is configured to expose the A2DP Sink role on your Bluetooth adapter
2. soundbridge talks to BlueZ (the Linux Bluetooth stack) over D-Bus to list paired devices, initiate connections, and monitor connection state
3. Once connected, PipeWire/PulseAudio routes the Bluetooth audio stream to your default output device

---

## Troubleshooting

**No icon in system tray**
Your desktop may not support the StatusNotifierItem protocol. Install a tray support extension:
- GNOME: install the *AppIndicator* extension from extensions.gnome.org
- KDE: works out of the box

**Device connects but no sound**
Make sure your phone selected **Media Audio** (not just calls). On Android: Bluetooth settings → your PC → check "Media audio".

**Connection fails**
Run soundbridge from a terminal to see error logs. Check that Bluetooth is on:
```bash
bluetoothctl show
```

**WirePlumber not detected**
On Ubuntu 22.04 with PulseAudio, the setup script installs a PulseAudio Bluetooth module instead. On Ubuntu 22.10+, PipeWire is used automatically.

---

## Contributing

Pull requests are welcome. If you have a bug or feature request, open an issue.

For a new distro, add the install commands to `setup.sh` under the right `case` branch and open a PR.

---

## License

MIT — see [LICENSE](LICENSE).
