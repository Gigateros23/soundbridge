#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Stopping soundbridge if running..."
pkill -f bluetooth-audio-connector 2>/dev/null || true

echo "==> Removing launcher..."
rm -f "$HOME/.local/bin/soundbridge"
rm -f "$HOME/.local/bin/bluetooth-audio-connector"

echo "==> Removing virtual environment..."
rm -rf "$SCRIPT_DIR/.venv"

echo "==> Removing settings..."
rm -rf "$HOME/.config/bluetooth-audio-connector"

echo "==> Removing WirePlumber A2DP Sink config..."
rm -f "$HOME/.config/wireplumber/wireplumber.conf.d/51-bluez-a2dp-sink.conf"
systemctl --user restart wireplumber 2>/dev/null || true

if [ -f "$HOME/.config/pulse/default.pa" ]; then
    echo "==> Removing PulseAudio Bluetooth config..."
    sed -i '/load-module module-bluetooth-discover/d' "$HOME/.config/pulse/default.pa"
    pulseaudio -k && pulseaudio --start 2>/dev/null || true
fi

echo ""
echo "soundbridge uninstalled. The source folder was not deleted."
echo "To remove it completely: rm -rf \"$SCRIPT_DIR\""
