#!/bin/bash
# rest_run_query.sh
#
# This script automates the entire process of querying the Trusted Data Agent API.
# It creates a session, submits a user's question, and then monitors the
# progress until a final result is received.
#
# Usage: ./rest_run_query.sh [--verbose] "Your question for the agent in quotes"

# --- 1. Argument Parsing and Validation ---
VERBOSE=false
USER_QUESTION=""
USER_UUID=""

# Check for --verbose flag
if [[ "$1" == "--verbose" ]]; then
  VERBOSE=true
  shift # Remove --verbose from arguments
fi

# Now, the first argument should be the user UUID, and the second should be the user question
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: ./rest_run_query.sh [--verbose] <user_uuid> \"<your_question>\"" >&2
  echo "Example: ./rest_run_query.sh --verbose a1b2c3d4-e5f6-7890-1234-567890abcdef \"What is the business description for the DEMO_DB database?\"" >&2
  exit 1
fi

USER_UUID="$1"
USER_QUESTION="$2"
BASE_URL="http://127.0.0.1:5000"

# Function to print messages, redirecting to stderr if not verbose
log_message() {
  if [ "$VERBOSE" = false ]; then
    echo "$@" >&2
  else
    echo "$@"
  fi
}

# --- 2. Check for Dependencies ---
if ! command -v jq &> /dev/null; then
    log_message "Error: 'jq' is not installed. Please install it to continue."
    log_message "On macOS: brew install jq"
    log_message "On Debian/Ubuntu: sudo apt-get install jq"
    exit 1
fi

if [ ! -x "./rest_check_status.sh" ]; then
    log_message "Error: 'rest_check_status.sh' not found or is not executable."
    log_message "Please ensure it is in the same directory and run 'chmod +x rest_check_status.sh'."
    exit 1
fi



# --- 4. Create a New Session ---
log_message "--> Step 1: Creating a new session..."
SESSION_ID=$(curl -s -X POST -H "X-TDA-User-UUID: $USER_UUID" "$BASE_URL/api/v1/sessions" | jq -r .session_id)

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
  log_message "Error: Failed to create a session. Is the server running and configured?"
  exit 1
fi
log_message "    Session created successfully: $SESSION_ID"
log_message ""

# --- 5. Submit the Query ---
log_message "--> Step 2: Submitting your query..."
JSON_PAYLOAD=$(jq -n --arg prompt "$USER_QUESTION" '{prompt: $prompt}')

TASK_URL=$(curl -s -X POST "$BASE_URL/api/v1/sessions/$SESSION_ID/query" \
     -H "Content-Type: application/json" \
     -H "X-TDA-User-UUID: $USER_UUID" \
     -d "$JSON_PAYLOAD" | jq -r .status_url)

if [ -z "$TASK_URL" ] || [ "$TASK_URL" = "null" ]; then
  log_message "Error: Failed to submit the query and get a task URL."
  exit 1
fi
log_message "    Query submitted. Task URL path is: $TASK_URL"
log_message ""


# --- 6. Run the Status Checker ---
log_message "--> Step 3: Starting the status checker. Monitoring for results..."
log_message "================================================================="

# Execute the status checking script, passing it the task URL, User UUID, and verbose flag.
if [ "$VERBOSE" = true ]; then
  ./rest_check_status.sh "$TASK_URL" "$USER_UUID" --verbose
else
  ./rest_check_status.sh "$TASK_URL" "$USER_UUID"
fi
