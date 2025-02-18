#!/usr/bin/env bash

# Install the airo-tulip package and other commands.
# This script will install the package to the current directory and create a Python 3.10 virtual environment.

# Check if the `pyenv` command is available.
if ! command -v pyenv &> /dev/null
then
    echo "pyenv could not be found. Please install pyenv and try again."
    exit
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
echo "Installing a Python 3.10 virtual environment to $(pwd)/env."
pyenv install 3.10 || { echo "Failed to install Python 3.10. Exiting..."; exit; }
pyenv local 3.10 || { echo "Failed to set the local Python version to 3.10. Exiting..."; exit; }
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
# Can't have direct dependencies with PyPI. Install airo-typing from the GitHub repository here.
pip install git+https://github.com/airo-ugent/airo-mono@main#subdirectory=airo-typing || { echo "Failed to install the airo-typing package. Exiting..."; exit; }
pip install airo-tulip || { echo "Failed to install the airo-tulip package. Exiting..."; exit; }
echo "Installing the dashboard server package."
pip install -e dashboard/ || { echo "Failed to install the dashboard package. Exiting..."; exit; }

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
copy_and_make_executable "start_dashboard"

# Make sure the dashboard server is run on boot.
# See: https://stackoverflow.com/a/9625233/18071096
mkdir -p /home/kelo/.local/share/tulip || { echo "Failed to create the tulip log directory. Exiting..."; exit; }
sudo bash -c '(crontab -l 2>/dev/null; echo "@reboot . /home/kelo/.kelorc ; $(pwd)/start_dashboard > ~/.local/share/tulip/dashboard_logs.txt 2>&1") | crontab -'

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
    reboot now
fi