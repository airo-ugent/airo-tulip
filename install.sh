#!/usr/bin/env bash
#
# System-wide installer for airo-tulip on a KELO CPU brick.
#
# Installs the server into /opt/airo-tulip, configuration into /etc/airo-tulip, and registers systemd
# services so the Zenoh router and the airo-tulip server start on boot. The packages are installed
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
echo "  services      : /etc/systemd/system/{zenoh,tulip}.service (run as root)"
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

# --- Zenoh router (zenohd) ---
if ! command -v zenohd &> /dev/null; then
    echo "Installing the Zenoh router (zenohd) from the Eclipse Zenoh apt repository..."
    echo "deb [trusted=yes] https://download.eclipse.org/zenoh/debian-repo/ /" \
        | sudo tee /etc/apt/sources.list.d/zenoh.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y zenoh
else
    echo "zenohd is already installed."
fi
ZENOHD_PATH="$(command -v zenohd)"

# --- Configuration ---
# Seed the platform config from the example on first install, but never clobber an edited one.
sudo mkdir -p "$CONFIG_DIR"
if [ ! -f "$ROBOT_CONFIG" ]; then
    sudo cp "$SOURCE_DIR/deploy/robot.example.yaml" "$ROBOT_CONFIG"
    echo "Created $ROBOT_CONFIG from the example. EDIT IT for your platform before driving (EtherCAT device + wheel layout)."
else
    echo "Using existing robot config at $ROBOT_CONFIG."
fi

# --- systemd services (rendered from deploy/*.service templates) ---
install_unit() {
    local name="$1"
    echo "Installing systemd unit: $name"
    sed -e "s|__ZENOHD__|${ZENOHD_PATH}|g" \
        -e "s|__SERVER_BIN__|${SERVER_BIN}|g" \
        -e "s|__CONFIG__|${ROBOT_CONFIG}|g" \
        "$SOURCE_DIR/deploy/${name}" \
        | sudo tee "/etc/systemd/system/${name}" > /dev/null
}
install_unit zenoh.service
install_unit tulip.service

sudo systemctl daemon-reload
echo "Enabling services on boot and (re)starting them..."
sudo systemctl enable zenoh.service tulip.service
# restart (not just start) so a re-run picks up changes to the units or the reinstalled server.
sudo systemctl restart zenoh.service
sudo systemctl restart tulip.service

echo
echo "Installation complete."
echo "  - Edit $ROBOT_CONFIG for your platform, then: sudo systemctl restart tulip"
echo "  - The source directory ($SOURCE_DIR) is no longer required and may be removed."
read -r -p "Reboot now to complete the installation? (y/N) " RESPONSE
if [ "$RESPONSE" = "y" ]; then
    sudo reboot now
fi
