#!/bin/bash

# Log the start time
echo "Starting Poetry Camera..." >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Navigate to the PoetryCamera directory
cd /home/shschubert/PoetryCamera || { echo "Failed to navigate to /home/shschubert/PoetryCamera" >> /home/shschubert/PoetryCamera/startup.log 2>&1; exit 1; }

# Source the virtual environment
source poetrycamera-env/bin/activate
echo "Virtual environment activated." >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Source .bashrc or .profile to include environment variables
source /home/shschubert/.bashrc
source /home/shschubert/.profile

# Set PYTHONPATH to include system site-packages
export PYTHONPATH=$PYTHONPATH:/usr/lib/python3/dist-packages
echo "PYTHONPATH: $PYTHONPATH" >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Log the Python path
echo "Python path: $(which python3)" >> /home/shschubert/PoetryCamera/startup.log 2>&1
echo "Python version: $(python3 --version)" >> /home/shschubert/PoetryCamera/startup.log 2>&1
echo "Environment variables: $(env)" >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Start the network connection check script
echo "Starting network connection check..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
python3 /home/shschubert/PoetryCamera/network-connection-check/connection_check.py >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
echo "Network connection check started." >> /home/shschubert/PoetryCamera/startup.log 2>&1

sleep 10

# Check if the OPENAI_API_KEY exists in the .env file
if grep -q "OPENAI_API_KEY" .env; then
    echo "OpenAI API key found. Starting with Gunicorn..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
    if python3 -c "import libcamera" &> /dev/null; then
        echo "libcamera is available." >> /home/shschubert/PoetryCamera/startup.log 2>&1
        # Start the Poetry Camera application using Gunicorn with the configuration file
        gunicorn -c gunicorn_config.py printer.scripts.cat_printer:app >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
        # Optionally call main.py to handle additional initializations if necessary
        python3 main.py >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
    else
        echo "libcamera not found, exiting..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
    fi
else
    echo "OpenAI API key not found. Please add it to the .env file." >> /home/shschubert/PoetryCamera/startup.log 2>&1
fi

# Log the completion of the script
echo "Poetry Camera started." >> /home/shschubert/PoetryCamera/startup.log 2>&1
