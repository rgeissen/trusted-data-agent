#!/bin/bash
# Test script for authentication UI

echo "Starting Trusted Data Agent with Authentication..."
echo ""

# Activate conda environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate mcp

# Set authentication environment variables
export TDA_AUTH_ENABLED=true
export TDA_JWT_SECRET_KEY=dev_secret_key_12345_change_in_production

# Start the server
echo "Server will be available at: http://127.0.0.1:5000"
echo "Login page: http://127.0.0.1:5000/login"
echo "Register page: http://127.0.0.1:5000/register"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m trusted_data_agent.main --host 127.0.0.1 --port 5000
