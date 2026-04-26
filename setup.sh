#!/usr/bin/env bash
set -e

echo "==> Installing system dependencies..."
sudo pacman -S --needed --noconfirm \
    python-gobject \
    python-dasbus \
    libayatana-appindicator \
    bluez \
    bluez-utils

echo "==> Enabling Bluetooth service..."
sudo systemctl enable --now bluetooth

echo "==> Installing WirePlumber A2DP Sink config..."
mkdir -p "$HOME/.config/wireplumber/wireplumber.conf.d"
cp wireplumber/51-bluez-a2dp-sink.conf \
    "$HOME/.config/wireplumber/wireplumber.conf.d/51-bluez-a2dp-sink.conf"

echo "==> Restarting WirePlumber..."
systemctl --user restart wireplumber

echo "==> Installing the app in a virtual environment..."
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e . --quiet

LAUNCHER="$HOME/.local/bin/bluetooth-audio-connector"
mkdir -p "$HOME/.local/bin"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$(pwd)/.venv/bin/bluetooth-audio-connector" "\$@"
EOF
chmod +x "$LAUNCHER"
echo "Launcher installed at $LAUNCHER"

echo ""
echo "Done! Run with: bluetooth-audio-connector"
echo ""
echo "To pair your phone:"
echo "  1. Run: bluetoothctl"
echo "  2. Commands: power on → discoverable on → pairable on → scan on"
echo "  3. Pair your phone, then on your phone connect to this PC via Bluetooth audio"
