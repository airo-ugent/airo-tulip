#!/usr/bin/env bash

# Install the airo-tulip package and other commands.
# This script will install the package to the current directory and create a Python 3.10 virtual environment.

# Check if the `uv` command is available.
if ! command -v uv &> /dev/null
then
    echo "uv could not be found. Please install uv and try again."
    echo "See: https://github.com/astral-sh/uv"
    exit
else
    echo "uv is installed."
fi

# Check if the user wants to install to the current directory.
echo "Continuing will install the airo-tulip package to the current directory: $(pwd)."
read -r -p "Do you want to continue? (y/N) " RESPONSE
if [ "$RESPONSE" != "y" ]
then
    echo "Exiting..."
    exit
fi

# Install the Python virtual environment.
echo "Running uv sync to create virtual environment at $(pwd)/.venv"
uv sync || { echo "Failed to create virtual environment. Exiting..."; exit; }

# Create a folder for our commands and copy them there.
mkdir -p bin || { echo "Failed to create the bin directory. Exiting..."; exit; }
cd bin || { echo "Failed to change to the bin directory. Exiting..."; exit; }

copy_and_make_executable() {
    local script_name=$1
    cp "../utils/${script_name}.sh" "${script_name}" || { echo "Failed to copy the ${script_name} command. Exiting..."; exit; }
    cp "../utils/${script_name}.py" "${script_name}.py" || { echo "Failed to copy the ${script_name} python script. Exiting..."; exit; }
    sudo chmod +x "${script_name}" || { echo "Failed to make the ${script_name} command executable. Exiting..."; exit; }
}

copy_and_make_executable "start_ur"
copy_and_make_executable "stop_ur"
copy_and_make_executable "start_tulip"
copy_and_make_executable "start_dashboard"

# Make sure the dashboard server is run on boot by creating a systemd service.
echo "Creating systemd service file at /etc/systemd/system/tulip-dashboard.service."
cat << EOF | sudo tee /etc/systemd/system/tulip-dashboard.service
[Unit]
Description=AIRO-tulip dashboard server
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=on-failure
RestartSec=1
User=kelo
ExecStart=bash -c ". /home/kelo/.kelorc ; $(pwd)/start_dashboard"

[Install]
WantedBy=multi-user.target
EOF
echo "Starting service."
sudo systemctl start tulip-dashboard
echo "Enabling service (start on boot)."
sudo systemctl enable tulip-dashboard

cd ..  # Back up out of bin for all following commands

# Prompt the user to add this path to the .bashrc file.
echo "Add the following lines to the /home/kelo/.kelorc file, and source it from /home/kelo/.bashrc to complete the installation."
echo "You can choose to do this manually, or we can do it for you."
echo "export AIRO_TULIP_PATH=\"$(pwd)\""
echo "export PATH=\"$(pwd)/bin:\$PATH\""
read -r -p "Can we add these lines to the .kelorc file for you and update .bashrc? (y/N) " RESPONSE
if [ "$RESPONSE" == "y" ]
then
  {
    echo -en '\n'
    echo "export AIRO_TULIP_PATH=\"$(pwd)\""
    echo "export PATH=\"$(pwd)/bin:\$PATH\""
  } > /home/kelo/.kelorc
  echo -e '\n# Added by the airo-tulip installation script.\nsource /home/kelo/.kelorc\n' >> /home/kelo/.bashrc
fi

echo "Installation complete! Reboot the machine to complete the installation, or manually start the dashboard server this once."
read -r -p "Do you want to reboot now? (y/N) " RESPONSE
if [ "$RESPONSE" == "y" ]
then
    sudo reboot now
fi