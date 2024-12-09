#!/usr/bin/env bash

# Install the airo-tulip package and other commands. This script must be run as the root user.
# This script will install the package to the current directory and create a Python 3.9 virtual environment.

if [ "$EUID" -ne 0 ]
  then echo "This script must be run as the root user."
  exit
fi

# Check if the `pyenv` command is available.
if ! command -v pyenv &> /dev/null
then
    echo "pyenv could not be found. Please install pyenv and try again."
else
    echo "pyenv is installed."
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
echo "Installing a Python 3.9 virtual environment to $(pwd)/env."
pyenv install 3.9 || { echo "Failed to install Python 3.9. Exiting..."; exit; }
pyenv local 3.9 || { echo "Failed to set the local Python version to 3.9. Exiting..."; exit; }
python -m venv env || { echo "Failed to create the Python virtual environment. Exiting..."; exit; }
source env/bin/activate || { echo "Failed to activate the Python virtual environment. Exiting..."; exit; }

# Check if everything above succeeded and we will use the correct Python executable.
python_executable=$(which python)
echo "Python executable: $python_executable"
if [ "$python_executable" != "$(pwd)/env/bin/python" ]
then
    echo "The Python executable is not the one in the virtual environment. Exiting..."
    exit
fi

# We can now install airo-tulip.
echo "Installing the airo-tulip package."
pip install airo-tulip || { echo "Failed to install the airo-tulip package. Exiting..."; exit; }
echo "Installing the dashboard server package."
pip install -e dashboard || { echo "Failed to install the dashboard package. Exiting..."; exit; }

# Create a folder for our commands and copy them there.
mkdir -p bin || { echo "Failed to create the bin directory. Exiting..."; exit; }
cd bin || { echo "Failed to change to the bin directory. Exiting..."; exit; }

copy_and_make_executable() {
    local script_name=$1
    cp "../utils/${script_name}.sh" "${script_name}" || { echo "Failed to copy the ${script_name} command. Exiting..."; exit; }
    cp "../utils/${script_name}.py" "${script_name}.py" || { echo "Failed to copy the ${script_name} python script. Exiting..."; exit; }
    chmod +x "${script_name}" || { echo "Failed to make the ${script_name} command executable. Exiting..."; exit; }
}

copy_and_make_executable "start_ur"
copy_and_make_executable "stop_ur"
copy_and_make_executable "start_tulip"
copy_and_make_executable "stop_tulip"
copy_and_make_executable "start_dashboard"

# Make sure the dashboard server is run on boot.
# See: https://stackoverflow.com/a/9625233/18071096
(crontab -l 2>/dev/null; echo "@reboot $(pwd)/start_dashboard") | crontab -

# Prompt the user to add this path to the .bashrc file.
echo "Add the following lines to the kelo user's .bashrc file to complete the installation."
echo "You can choose to do this manually, or we can do it for you."
echo "export AIRO_TULIP_PATH=\"$(pwd)\""
echo "export PATH=\"$(pwd)/bin:\$PATH\""
read -r -p "Can we add these lines to the .bashrc file for you? (y/N) " RESPONSE
if [ "$RESPONSE" == "y" ]
then
    echo "export AIRO_TULIP_PATH=\"$(pwd)\"" >> /home/kelo/.bashrc
    echo "export PATH=\"$(pwd)/bin:\$PATH\"" >> /home/kelo/.bashrc
fi

echo "Installation complete! Please restart the shell or run the following commands to complete the installation."
echo "source /home/kelo/.bashrc"
