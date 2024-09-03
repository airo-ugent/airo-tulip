#!/usr/bin/env bash

# Start the TULIP server. Temporary. In the future, this should be a binary that is run on server boot.

if [ "$EUID" -ne 0 ]
  then echo "This script must be run as the root user"
  exit
fi

sleep 60
cd /home/kelo || { echo /home/kelo does not exist & exit; }
cd airo-tulip || { echo airo-tulip directory does not exist  && exit; }
source env/bin/activate
cd airo-tulip/scripts || { echo airo-tulip/scripts directory does not exist  && exit; }
python test_server.py
