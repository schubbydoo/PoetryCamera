#!/bin/bash

# Log the start time
echo "Starting Poetry Camera..." >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Wait for the system to be ready
echo "Waiting for system to be ready..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
sleep 15  # Adjust this if necessary

# Navigate to the PoetryCamera directory
cd /home/shschubert/PoetryCamera || { echo "Failed to navigate to /home/shschubert/PoetryCamera" >> /home/shschubert/PoetryCamera/startup.log 2>&1; exit 1; }

# Source the virtual environment
echo "Sourcing virtual environment..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
source poetrycamera-env/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment" >> /home/shschubert/PoetryCamera/startup.log 2>&1
    exit 1
fi
echo "Virtual environment activated." >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Set PYTHONPATH to include system site-packages
export PYTHONPATH=$PYTHONPATH:/usr/lib/python3/dist-packages
echo "PYTHONPATH: $PYTHONPATH" >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Log the Python path and version
echo "Python path: $(which python3)" >> /home/shschubert/PoetryCamera/startup.log 2>&1
echo "Python version: $(python3 --version)" >> /home/shschubert/PoetryCamera/startup.log 2>&1
echo "Environment variables: $(env)" >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Start the network connection check script
echo "Starting network connection check..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
python3 /home/shschubert/PoetryCamera/network-connection-check/connection_check.py >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
if [ $? -ne 0 ]; then
    echo "Failed to start network connection check script" >> /home/shschubert/PoetryCamera/startup.log 2>&1
    exit 1
fi
echo "Network connection check started." >> /home/shschubert/PoetryCamera/startup.log 2>&1

# Start the Web Interface on port 8000 (always running)
echo "Starting Web Interface on port 8000..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
python3 -m gunicorn -c gunicorn_config.py --bind 0.0.0.0:8000 web_interface.app:app >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
if [ $? -ne 0 ]; then
    echo "Failed to start Web Interface" >> /home/shschubert/PoetryCamera/startup.log 2>&1
else
    echo "Web Interface started on port 8000." >> /home/shschubert/PoetryCamera/startup.log 2>&1
fi

# Check if the OPENAI_API_KEY exists in the .env file
if grep -q "OPENAI_API_KEY" .env; then
    echo "OpenAI API key found. Starting Poetry Camera..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
    if python3 -c "import libcamera" &> /dev/null; then
        echo "libcamera is available." >> /home/shschubert/PoetryCamera/startup.log 2>&1

        # Ensure no other process is using the camera
        sudo fuser -k /dev/video0
        sudo fuser -k /dev/media0

        # Start the Cat Printer service using Gunicorn
        echo "Starting Cat Printer service on port 5002..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
        gunicorn -c gunicorn_config.py printer.scripts.cat_printer:app --bind 0.0.0.0:5002 >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
        if [ $? -ne 0 ]; then
            echo "Failed to start Cat Printer service" >> /home/shschubert/PoetryCamera/startup.log 2>&1
            exit 1
        fi
        echo "Cat Printer service started on port 5002." >> /home/shschubert/PoetryCamera/startup.log 2>&1

        # Start the main Poetry Camera application
        echo "Starting main.py..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
        python3 main.py >> /home/shschubert/PoetryCamera/startup.log 2>&1 &
        if [ $? -ne 0 ]; then
            echo "Failed to start main.py" >> /home/shschubert/PoetryCamera/startup.log 2>&1
            exit 1
        fi
        echo "main.py started." >> /home/shschubert/PoetryCamera/startup.log 2>&1
    else
        echo "libcamera not found, exiting..." >> /home/shschubert/PoetryCamera/startup.log 2>&1
        exit 1
    fi
else
    echo "OpenAI API key not found. Please add it to the .env file." >> /home/shschubert/PoetryCamera/startup.log 2>&1
    echo "Web Interface is still running - configure API key via Settings page." >> /home/shschubert/PoetryCamera/startup.log 2>&1
fi

# Log the completion of the script
echo "Poetry Camera startup complete." >> /home/shschubert/PoetryCamera/startup.log 2>&1
