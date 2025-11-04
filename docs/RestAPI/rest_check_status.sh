#!/bin/bash
# check_status.sh
#
# This script polls a task status URL until the task is complete,
# printing new events as they arrive.

# --- 1. Argument Parsing and Validation ---
VERBOSE=false
TASK_URL_PATH=""
USER_UUID=""

# Parse arguments
while (( "$#" )); do
  case "$1" in
    --verbose)
      VERBOSE=true
      ;;
    -*)
      echo "Unsupported flag $1" >&2
      exit 1
      ;;
    *)
      if [ -z "$TASK_URL_PATH" ]; then
        TASK_URL_PATH=$1
      elif [ -z "$USER_UUID" ]; then
        USER_UUID=$1
      else
        echo "Too many arguments provided." >&2
        exit 1
      fi
      ;;
  esac
  shift
done

# Check if required arguments are present
if [ -z "$TASK_URL_PATH" ] || [ -z "$USER_UUID" ]; then
  echo "Usage: ./check_status.sh <task_url_path> <user_uuid> [--verbose]" >&2
  echo "Example: ./check_status.sh /api/v1/tasks/some-task-id a1b2c3d4-e5f6-7890-1234-567890abcdef --verbose" >&2
  exit 1
fi

# Function to print messages, redirecting to stderr if not verbose
log_message() {
  if [ "$VERBOSE" = false ]; then
    echo "$@" >&2
  else
    echo "$@"
  fi
}

# --- 2. Initialization ---
BASE_URL="http://127.0.0.1:5000"
FULL_URL="$BASE_URL$TASK_URL_PATH"
EVENTS_SEEN=0

log_message "Polling status for task at: $FULL_URL"
log_message "-------------------------------------"

# --- 3. Polling Loop ---
while true; do
  # Fetch the latest task status, including the User UUID header
  RESPONSE=$(curl -s -H "X-TDA-User-UUID: $USER_UUID" "$FULL_URL")

  # Gracefully handle cases where the server response is empty
  if [ -z "$RESPONSE" ]; then
    log_message "Warning: Received empty response from server. Retrying..."
    sleep 2
    continue
  fi

  # --- Print NEW events ---
  # Safely get the total number of events, providing a default of 0
  TOTAL_EVENTS=$(echo "$RESPONSE" | jq '(.events | length) // 0')

  # Add a final check to ensure TOTAL_EVENTS is a number before comparison
  if ! [[ "$TOTAL_EVENTS" =~ ^[0-9]+$ ]]; then
    log_message "Warning: Could not parse event count from response. The response may not be valid JSON."
    TOTAL_EVENTS=$EVENTS_SEEN # Avoid breaking the loop; use the last known good count
  fi

  # Check if there are more events now than we've seen before
  if [ "$TOTAL_EVENTS" -gt "$EVENTS_SEEN" ]; then
    # If so, get only the new events
    NEW_EVENTS=$(echo "$RESPONSE" | jq -c ".events[$EVENTS_SEEN:] | .[]")

    # Print each new event, formatting with jq for readability
    if [ "$VERBOSE" = true ]; then
      echo "$NEW_EVENTS" | jq
    fi

    # Update the count of events we've seen
    EVENTS_SEEN=$TOTAL_EVENTS
  fi

  # --- Check for completion ---
  STATUS=$(echo "$RESPONSE" | jq -r .status)
  if [[ "$STATUS" == "complete" || "$STATUS" == "error" || "$STATUS" == "cancelled" ]]; then # Added cancelled status check
    log_message "-------------------------------------"
    log_message "--- FINAL STATUS: $STATUS ---"
    log_message "--- FINAL RESULT ---"
    echo "$RESPONSE" | jq '.result' # Always print final result to stdout
    break
  fi

  sleep 1
done