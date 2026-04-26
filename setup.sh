#!/usr/bin/env bash
set -e

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

install_deps_arch() {
    sudo pacman -S --needed --noconfirm \
        python-gobject \
        python-dasbus \
        libayatana-appindicator \
        libnotify \
        bluez \
        bluez-utils
}

install_deps_ubuntu() {
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3-gi \
        python3-gi-cairo \
        gir1.2-gtk-3.0 \
        gir1.2-ayatanaappindicator3-0.1 \
        gir1.2-notify-0.7 \
        python3-dasbus \
        bluez \
        pulseaudio-module-bluetooth 2>/dev/null || true
}

install_deps_fedora() {
    sudo dnf install -y \
        python3-gobject \
        python3-dasbus \
        libayatana-appindicator-gtk3 \
        libnotify \
        bluez
}

setup_wireplumber() {
    echo "==> Configuring WirePlumber (A2DP Sink)..."
    mkdir -p "$HOME/.config/wireplumber/wireplumber.conf.d"
    cp wireplumber/51-bluez-a2dp-sink.conf \
        "$HOME/.config/wireplumber/wireplumber.conf.d/51-bluez-a2dp-sink.conf"
    systemctl --user restart wireplumber
}

setup_pulseaudio() {
    echo "==> Configuring PulseAudio (A2DP Sink)..."
    mkdir -p "$HOME/.config/pulse"
    PACONF="$HOME/.config/pulse/default.pa"
    if ! grep -q "module-bluetooth-discover" "$PACONF" 2>/dev/null; then
        echo ".include /etc/pulse/default.pa" >> "$PACONF"
        echo "load-module module-bluetooth-discover" >> "$PACONF"
    fi
    pulseaudio -k && pulseaudio --start || true
}

setup_audio() {
    if systemctl --user is-active --quiet wireplumber 2>/dev/null; then
        setup_wireplumber
    elif systemctl --user is-active --quiet pipewire 2>/dev/null; then
        setup_wireplumber
    else
        setup_pulseaudio
    fi
}

install_app() {
    echo "==> Installing the app..."
    python3 -m venv --system-site-packages .venv
    .venv/bin/pip install -e . --quiet

    LAUNCHER="$HOME/.local/bin/soundbridge"
    mkdir -p "$HOME/.local/bin"
    cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$(pwd)/.venv/bin/bluetooth-audio-connector" "\$@"
EOF
    chmod +x "$LAUNCHER"
    echo "Launcher installed: $LAUNCHER"
}

DISTRO=$(detect_distro)
echo "==> Detected distro: $DISTRO"

echo "==> Installing system dependencies..."
case "$DISTRO" in
    arch|cachyos|manjaro|endeavouros|garuda)
        install_deps_arch
        ;;
    ubuntu|debian|linuxmint|pop)
        install_deps_ubuntu
        ;;
    fedora|rhel|centos|rocky|alma)
        install_deps_fedora
        ;;
    *)
        echo "Unsupported distro: $DISTRO"
        echo "Install manually: python3-gobject, python3-dasbus, libayatana-appindicator, bluez"
        exit 1
        ;;
esac

echo "==> Enabling Bluetooth..."
sudo systemctl enable --now bluetooth

setup_audio
install_app

echo ""
echo "Done! Run: soundbridge"
echo ""
echo "First time? Pair your phone:"
echo "  bluetoothctl"
echo "  > power on"
echo "  > discoverable on"
echo "  > pairable on"
echo "  > scan on"
echo "  Then pair from your phone's Bluetooth settings."
