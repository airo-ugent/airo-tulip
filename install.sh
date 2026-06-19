#!/usr/bin/env bash
#
# Install the airo-tulip packages and supporting services on a KELO CPU brick.
#
# This script is idempotent: it is safe to re-run. It installs to the directory in which it lives.
# The services run as the invoking user by default; override with AIRO_TULIP_USER=<user>.

set -euo pipefail

err() { echo "ERROR: $*" >&2; exit 1; }
trap 'err "installation failed on line $LINENO."' ERR

# Install location is this script's own directory (the repository root).
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$INSTALL_DIR"

SERVER_BIN="$INSTALL_DIR/.venv/bin/airo-tulip-server"
ROBOT_CONFIG="$INSTALL_DIR/robot.yaml"

# The user the services run as, and their home (for .kelorc / .bashrc).
TARGET_USER="${AIRO_TULIP_USER:-$USER}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6 || true)"
TARGET_HOME="${TARGET_HOME:-/home/$TARGET_USER}"
KELORC="$TARGET_HOME/.kelorc"
BASHRC="$TARGET_HOME/.bashrc"

echo "Install dir: $INSTALL_DIR"
echo "Services will run as user: $TARGET_USER (home: $TARGET_HOME)"

# --- Preconditions ---

command -v uv &> /dev/null || err "uv could not be found. Install it first: https://github.com/astral-sh/uv"
echo "uv is installed."

read -r -p "Continue installing to $INSTALL_DIR? (y/N) " RESPONSE
[ "$RESPONSE" = "y" ] || { echo "Exiting..."; exit 0; }

# --- Python environment (installs all workspace packages, incl. console scripts) ---

echo "Running uv sync to create the virtual environment at $INSTALL_DIR/.venv ..."
uv sync

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

# --- Robot configuration ---
# The server reads its platform config (EtherCAT device + drive layout) from a YAML file. Seed it from
# the example on first install, but never clobber an existing (edited) config.
if [ ! -f "$ROBOT_CONFIG" ]; then
    cp "$INSTALL_DIR/deploy/robot.example.yaml" "$ROBOT_CONFIG"
    echo "Created $ROBOT_CONFIG from the example. EDIT IT for your platform before driving (EtherCAT device + wheel layout)."
else
    echo "Using existing robot config at $ROBOT_CONFIG."
fi

# --- systemd services (rendered from deploy/*.service templates) ---
# zenoh.service: the Zenoh router. tulip.service: the airo-tulip drive-control server (runs on boot;
# the drives can be disabled at runtime to save energy via a KELORobile client).

install_unit() {
    local name="$1"
    echo "Installing systemd unit: $name"
    sed -e "s|__USER__|${TARGET_USER}|g" \
        -e "s|__ZENOHD__|${ZENOHD_PATH}|g" \
        -e "s|__SERVER_BIN__|${SERVER_BIN}|g" \
        -e "s|__CONFIG__|${ROBOT_CONFIG}|g" \
        "$INSTALL_DIR/deploy/${name}" \
        | sudo tee "/etc/systemd/system/${name}" > /dev/null
}

install_unit zenoh.service
install_unit tulip.service

sudo systemctl daemon-reload
echo "Enabling services on boot and (re)starting them..."
sudo systemctl enable zenoh.service tulip.service
# restart (not just start) so a re-run picks up any changes to the unit files.
sudo systemctl restart zenoh.service
sudo systemctl restart tulip.service

# --- Environment (.kelorc + .bashrc), idempotent ---
# Exposes the virtual environment (and any console scripts it provides) on PATH.

read -r -p "Add airo-tulip environment variables to $KELORC and source it from $BASHRC? (y/N) " RESPONSE
if [ "$RESPONSE" = "y" ]; then
    MARKER_START="# >>> airo-tulip >>>"
    MARKER_END="# <<< airo-tulip <<<"

    touch "$KELORC"
    # Replace any previously-installed block rather than appending or clobbering the whole file.
    sed -i "/$MARKER_START/,/$MARKER_END/d" "$KELORC"
    {
        echo "$MARKER_START"
        echo "export AIRO_TULIP_PATH=\"$INSTALL_DIR\""
        echo "export PATH=\"$INSTALL_DIR/.venv/bin:\$PATH\""
        echo "$MARKER_END"
    } >> "$KELORC"
    echo "Updated $KELORC."

    touch "$BASHRC"
    if ! grep -qF "source $KELORC" "$BASHRC"; then
        printf '\n# Added by the airo-tulip installation script.\nsource %s\n' "$KELORC" >> "$BASHRC"
        echo "Added 'source $KELORC' to $BASHRC."
    else
        echo "$BASHRC already sources $KELORC."
    fi
fi

echo "Installation complete!"
read -r -p "Reboot now to complete the installation? (y/N) " RESPONSE
if [ "$RESPONSE" = "y" ]; then
    sudo reboot now
fi
