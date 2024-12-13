#!/usr/bin/env bash

# Install the airo-tulip package and other commands.
# This script will install the package to the current directory and create a Python 3.9 virtual environment.

# Check if the `conda` command is available.
if ! command -v conda &> /dev/null
then
    echo "conda could not be found. Please install anaconda/miniconda and try again."
    exit
else
    echo "conda is installed."
fi

# Check if the user wants to install to the current directory.
echo "Continuing will install the airo-tulip package to the current directory: $(pwd)."
read -r -p "Do you want to continue? (y/N) " RESPONSE
if [ "$RESPONSE" != "y" ]
then
    echo "Exiting..."
    exit
fi

# Create a new conda environment for the installation.
echo "Creating a conda environment. Enter a name for the new environment."
read -r -p "Environment name: " ENV_NAME
conda create --name "$ENV_NAME" python=3.9 || { echo "Failed to create the conda environment. Exiting..."; exit; }
echo "Conda environment created."
conda activate "$ENV_NAME" || { echo "Failed to activate the conda environment. Exiting..."; exit; }

# Check if everything above succeeded and we will use the correct Python executable.
python_executable=$(which python)
echo "Python executable: $python_executable"
# Check if the user wants to continue with the current Python executable.
read -r -p "Do you want to continue with this Python executable? (y/N) " RESPONSE
if [ "$RESPONSE" != "y" ]
then
    echo "Exiting..."
    exit
fi

# We can now install airo-tulip.
echo "Installing the airo-tulip package."
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
# copy_and_make_executable "stop_tulip"
copy_and_make_executable "start_dashboard"

cp "../utils/cyclone_config.xml" "cyclone_config.xml" || { echo "Failed to copy the cyclone_config.xml file. Exiting..."; exit; }

# Make sure the dashboard server is run on boot.
# See: https://stackoverflow.com/a/9625233/18071096
# TODO: does this need to be run as root?
sudo bash -c '(crontab -l 2>/dev/null; echo "@reboot $(pwd)/start_dashboard") | crontab -'

cd ..  # Back up out of bin for all following commands

# Prompt the user to add this path to the .bashrc file.
echo "Add the following lines to the kelo user's .bashrc file to complete the installation."
echo "You can choose to do this manually, or we can do it for you."
echo "export AIRO_TULIP_PATH=\"$(pwd)\""
echo "export PATH=\"$(pwd)/bin:\$PATH\""
echo "export CYCLONEDDS_URI=\"$(pwd)/bin/cyclone_config.xml\""
read -r -p "Can we add these lines to the .bashrc file for you? (y/N) " RESPONSE
if [ "$RESPONSE" == "y" ]
then
  {
    echo -en '\n'
    echo "# Added by the airo-tulip installation script."
    echo "export AIRO_TULIP_PATH=\"$(pwd)\""
    echo "export PATH=\"$(pwd)/bin:\$PATH\""
    echo "export CYCLONEDDS_URI=\"$(pwd)/bin/cyclone_config.xml\""
    echo -en '\n'
  } >> /home/kelo/.bashrc
fi

echo "Installation complete! Reboot the machine to complete the installation, or manually start the dashboard server this once."
read -r -p "Do you want to reboot now? (y/N) " RESPONSE
if [ "$RESPONSE" == "y" ]
then
    reboot now
fi
