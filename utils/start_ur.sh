#!/usr/bin/env bash

# Start the UR arm server. Temporary. In the future, this should be a binary that is run on server boot.

if [ "$EUID" -ne 0 ]
  then echo "This script must be run as the root user"
  exit
fi

sleep 60
cd /home/kelo || { echo /home/kelo does not exist & exit; }
cd airo-tulip || { echo airo-tulip directory does not exist  && exit; }
source env/bin/activate
cd utils || { echo utils directory does not exist  && exit; }
python start_ur.py --ip 10.42.0.1 --installation robotiq
