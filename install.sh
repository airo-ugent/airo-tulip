#!/usr/bin/env bash
#
# System-wide installer for airo-tulip on a KELO CPU brick.
#
# Installs the server into /opt/airo-tulip, configuration into /etc/airo-tulip, and registers a systemd
# service so the airo-tulip server starts on boot. The server runs in Zenoh peer mode and listens for
# direct client connections, so no Zenoh router (zenohd) is needed. The packages are installed
# non-editable, so after installation the source clone is no longer needed and may be removed.
#
# For DEVELOPMENT (no system changes, no systemd), do NOT run this script — see the README.

set -euo pipefail

err() { echo "ERROR: $*" >&2; exit 1; }
trap 'err "installation failed on line $LINENO."' ERR

# Fixed system-wide locations.
INSTALL_PREFIX="/opt/airo-tulip"
VENV_DIR="$INSTALL_PREFIX/venv"
SERVER_BIN="$VENV_DIR/bin/airo-tulip-server"
CONFIG_DIR="/etc/airo-tulip"
ROBOT_CONFIG="$CONFIG_DIR/robot.yaml"
SYMLINK="/usr/local/bin/airo-tulip-server"

# The source tree to build from (this script's directory). Only needed at install time.
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v uv &> /dev/null || err "uv could not be found. Install it first: https://github.com/astral-sh/uv"
UV="$(command -v uv)"

echo "This will install airo-tulip system-wide:"
echo "  server + venv : $INSTALL_PREFIX"
echo "  configuration : $ROBOT_CONFIG"
echo "  command       : $SYMLINK"
echo "  service       : /etc/systemd/system/tulip.service (runs as root)"
echo "It uses sudo and needs network access."
read -r -p "Continue? (y/N) " RESPONSE
[ "$RESPONSE" = "y" ] || { echo "Exiting..."; exit 0; }

# --- Build + install the packages into a venv under /opt (non-editable) ---
echo "Creating virtual environment at $VENV_DIR ..."
sudo mkdir -p "$INSTALL_PREFIX"
sudo "$UV" venv --python 3.10 "$VENV_DIR"
echo "Building and installing airo-tulip and airo-tulip-hal into $VENV_DIR ..."
sudo "$UV" pip install --python "$VENV_DIR/bin/python" "$SOURCE_DIR/airo-tulip" "$SOURCE_DIR/airo-tulip-hal"

# Expose the server command system-wide.
sudo ln -sf "$SERVER_BIN" "$SYMLINK"

# --- Configuration ---
# Seed the platform config from the example on first install, but never clobber an edited one.
sudo mkdir -p "$CONFIG_DIR"
if [ ! -f "$ROBOT_CONFIG" ]; then
    sudo cp "$SOURCE_DIR/deploy/robot.example.yaml" "$ROBOT_CONFIG"
    echo "Created $ROBOT_CONFIG from the example. EDIT IT for your platform before driving (EtherCAT device + wheel layout)."
else
    echo "Using existing robot config at $ROBOT_CONFIG."
fi

# --- systemd service (rendered from the deploy/*.service template) ---
install_unit() {
    local name="$1"
    echo "Installing systemd unit: $name"
    sed -e "s|__SERVER_BIN__|${SERVER_BIN}|g" \
        -e "s|__CONFIG__|${ROBOT_CONFIG}|g" \
        "$SOURCE_DIR/deploy/${name}" \
        | sudo tee "/etc/systemd/system/${name}" > /dev/null
}
install_unit tulip.service

sudo systemctl daemon-reload
echo "Enabling the service on boot and (re)starting it..."
sudo systemctl enable tulip.service
# restart (not just start) so a re-run picks up changes to the unit or the reinstalled server.
sudo systemctl restart tulip.service

echo
echo "Installation complete."
echo "  - Edit $ROBOT_CONFIG for your platform, then: sudo systemctl restart tulip"
echo "  - The source directory ($SOURCE_DIR) is no longer required and may be removed."
read -r -p "Reboot now to complete the installation? (y/N) " RESPONSE
if [ "$RESPONSE" = "y" ]; then
    sudo reboot now
fi
