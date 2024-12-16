#!/usr/bin/env bash

if [ -z "${AIRO_TULIP_PATH}" ]; then
    echo "AIRO_TULIP_PATH is unset or set to the empty string."
    echo "Your installation may be incomplete. Exiting..."
    exit
fi

cd "${AIRO_TULIP_PATH}" || { echo "Failed to change to the ${AIRO_TULIP_PATH} directory. Exiting..."; exit; }

source env/bin/activate

python_executable=$(which python)
echo "Python executable: $python_executable"
if [ "$python_executable" != "$(pwd)/env/bin/python" ]
then
    echo "The Python executable is not the one in the virtual environment. Exiting..."
    exit
fi

cd bin || { echo "Failed to change to the bin directory. Exiting..."; exit; }

python start_dashboard.py &
