#!/bin/bash
# check_status.sh
#
# This script polls a task status URL until the task is complete,
# printing new events as they arrive.

# --- 1. Argument Validation ---
# Check if a task URL path was provided as an argument.
if [ -z "$1" ]; then
  echo "Usage: ./check_status.sh "
  echo "Example: ./check_status.sh /api/v1/tasks/some-task-id"
  exit 1
fi

# --- 2. Initialization ---
TASK_URL_PATH=$1
BASE_URL="http://127.0.0.1:5000"
FULL_URL="$BASE_URL$TASK_URL_PATH"
EVENTS_SEEN=0

echo "Polling status for task at: $FULL_URL"
echo "-------------------------------------"

# --- 3. Polling Loop ---
while true; do
  # Fetch the latest task status
  RESPONSE=$(curl -s "$FULL_URL")
  
  # Gracefully handle cases where the server response is empty
  if [ -z "$RESPONSE" ]; then
    echo "Warning: Received empty response from server. Retrying..."
    sleep 2
    continue
  fi

  # --- Print NEW events ---
  # Safely get the total number of events, providing a default of 0
  TOTAL_EVENTS=$(echo "$RESPONSE" | jq '(.events | length) // 0')
  
  # Add a final check to ensure TOTAL_EVENTS is a number before comparison
  if ! [[ "$TOTAL_EVENTS" =~ ^[0-9]+$ ]]; then
    echo "Warning: Could not parse event count from response. The response may not be valid JSON."
    TOTAL_EVENTS=$EVENTS_SEEN # Avoid breaking the loop; use the last known good count
  fi

  # Check if there are more events now than we've seen before
  if [ "$TOTAL_EVENTS" -gt "$EVENTS_SEEN" ]; then
    # If so, get only the new events
    NEW_EVENTS=$(echo "$RESPONSE" | jq -c ".events[$EVENTS_SEEN:] | .[]")
    
    # Print each new event, formatting with jq for readability
    echo "$NEW_EVENTS" | jq
    
    # Update the count of events we've seen
    EVENTS_SEEN=$TOTAL_EVENTS
  fi

  # --- Check for completion ---
  STATUS=$(echo "$RESPONSE" | jq -r .status)
  if [ "$STATUS" = "complete" ] || [ "$STATUS" = "error" ]; then
    echo "-------------------------------------"
    echo "--- FINAL STATUS: $STATUS ---"
    echo "--- FINAL RESULT ---"
    echo "$RESPONSE" | jq '.result'
    break
  fi
  
  sleep 1
done
