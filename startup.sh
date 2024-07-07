#!/bin/bash

# Navigate to the PoetryCamera directory
cd /home/shschubert/PoetryCamera || { echo "Failed to navigate to /home/shschubert/PoetryCamera"; exit 1; }

# Source the virtual environment
source poetrycamera-env/bin/activate

# Check if the OPENAI_API_KEY exists in the .env file
if grep -q "OPENAI_API_KEY" .env; then
    echo "OpenAI API key found. Starting main.py..."
    python3 main.py
else
    echo "OpenAI API key not found. Please add it to the .env file."
fi

