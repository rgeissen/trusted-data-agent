#!/bin/bash
# rest_run_query.sh
#
# This script automates the entire process of querying the Trusted Data Agent API.
# It creates a session, submits a user's question, and then monitors the
# progress until a final result is received.
#
# Usage: ./rest_run_query.sh "Your question for the agent in quotes"

# --- 1. Input Validation ---
# Check if a user question was provided as an argument.
if [ -z "$1" ]; then
  echo "Usage: ./rest_run_query.sh \"<your_question>\""
  echo "Example: ./rest_run_query.sh \"What is the business description for the DEMO_DB database?\""
  exit 1
fi

USER_QUESTION="$1"
BASE_URL="http://127.0.0.1:5000"

# --- 2. Check for Dependencies ---
# Ensure the jq command-line JSON processor is installed.
if ! command -v jq &> /dev/null; then
    echo "Error: 'jq' is not installed. Please install it to continue."
    echo "On macOS: brew install jq"
    echo "On Debian/Ubuntu: sudo apt-get install jq"
    exit 1
fi

# Ensure the check_status.sh script exists and is executable.
if [ ! -x "./rest_check_status.sh" ]; then
    echo "Error: 'rest_check_status.sh' not found or is not executable."
    echo "Please ensure it is in the same directory and run 'chmod +x rest_check_status.sh'."
    exit 1
fi

# --- 3. Create a New Session ---
echo "--> Step 1: Creating a new session..."
SESSION_ID=$(curl -s -X POST "$BASE_URL/api/v1/sessions" | jq -r .session_id)

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
  echo "Error: Failed to create a session. Is the server running and configured?"
  exit 1
fi
echo "    Session created successfully: $SESSION_ID"
echo ""

# --- 4. Submit the Query ---
echo "--> Step 2: Submitting your query..."
# We use jq to construct the JSON payload to handle special characters correctly.
JSON_PAYLOAD=$(jq -n --arg prompt "$USER_QUESTION" '{prompt: $prompt}')

TASK_URL=$(curl -s -X POST "$BASE_URL/api/v1/sessions/$SESSION_ID/query" \
     -H "Content-Type: application/json" \
     -d "$JSON_PAYLOAD" | jq -r .status_url)

if [ -z "$TASK_URL" ] || [ "$TASK_URL" = "null" ]; then
  echo "Error: Failed to submit the query and get a task URL."
  exit 1
fi
echo "    Query submitted. Task URL path is: $TASK_URL"
echo ""


# --- 5. Run the Status Checker ---
echo "--> Step 3: Starting the status checker. Monitoring for results..."
echo "================================================================="
# Execute the status checking script, passing it the task URL.
./rest_check_status.sh "$TASK_URL"

