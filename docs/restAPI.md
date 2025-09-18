# Trusted Data Agent REST API Documentation

## 1. Introduction

Welcome to the Trusted Data Agent (TDA) REST API. This API provides a programmatic interface to interact with the agent's powerful data analysis and querying capabilities.

The API is designed around an **asynchronous task-based architecture**. This pattern is ideal for handling potentially long-running agent processes in a robust and scalable way. Instead of holding a connection open while the agent works, you initiate a task and then poll a status endpoint to get progress updates and the final result.

This document provides a comprehensive guide to all available endpoints and data models.

## 2. Authentication

The current version of the REST API (v1) does not require authentication. Access is unrestricted. Future versions may introduce API key or OAuth-based authentication.

## 3. API Endpoints

The base URL for all endpoints is `/api`.

### 3.1. Create a New Session

Creates a new, isolated conversation session for the agent. A session stores context and history for subsequent queries.

* **Endpoint**: `POST /v1/sessions`
* **Method**: `POST`
* **Body**: None
* **Success Response**:
    * **Code**: `201 Created`
    * **Content**:
        ```json
        {
          "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
        }
        ```
* **Error Response**:
    * **Code**: `503 Service Unavailable` (if LLM/MCP services are not configured)
    * **Content**:
        ```json
        {
          "error": "Application is not configured. Please connect to LLM and MCP services first."
        }
        ```

### 3.2. Submit a Query

Submits a natural language query to a specific session. This initiates a background task for the agent to process the query.

* **Endpoint**: `POST /v1/sessions/{session_id}/query`
* **Method**: `POST`
* **URL Parameters**:
    * `session_id` (string, required): The unique identifier for the session, obtained from the "Create a New Session" endpoint.
* **Body**:
    ```json
    {
      "prompt": "Your natural language query for the agent."
    }
    ```
* **Success Response**:
    * **Code**: `202 Accepted`
    * **Content**:
        ```json
        {
          "task_id": "task-9876-5432-1098-7654",
          "status_url": "/api/v1/tasks/task-9876-5432-1098-7654"
        }
        ```
* **Error Responses**:
    * **Code**: `404 Not Found` (if `session_id` is invalid)
    * **Code**: `400 Bad Request` (if the `prompt` field is missing from the request body)

### 3.3. Get Task Status and Result

Polls for the status of a background task. This endpoint provides real-time progress updates through an event log and delivers the final result when the task is complete.

* **Endpoint**: `GET /v1/tasks/{task_id}`
* **Method**: `GET`
* **URL Parameters**:
    * `task_id` (string, required): The unique identifier for the task, obtained from the "Submit a Query" endpoint.
* **Success Responses**:
    * **Code**: `200 OK`
    * See section **4. The Task Object** for detailed response content.
* **Error Response**:
    * **Code**: `404 Not Found` (if `task_id` is invalid)

## 4. The Task Object

The Task Object is the central data structure for monitoring a query. It is returned by the `GET /v1/tasks/{task_id}` endpoint.

### 4.1. Structure

```json
{
  "task_id": "string",
  "status": "string",
  "last_updated": "string (ISO 8601 UTC)",
  "events": [
    {
      "timestamp": "string (ISO 8601 UTC)",
      "event_data": { ... },
      "event_type": "string"
    }
  ],
  "intermediate_data": [
    {
      "tool_name": "string",
      "data": [ ... ]
    }
  ],
  "result": { ... }
}
```

### 4.2. Fields

* `task_id`: The unique ID of the task.
* `status`: The current state of the task (`pending`, `processing`, `complete`, or `error`).
* `last_updated`: The UTC timestamp of the last update to this task object.
* `events`: A chronological log of events from the agent's execution process.
* `intermediate_data`: A list of successful data results from tool calls as they are generated.
* `result`: The final, structured output from the agent. This field is `null` until the `status` is `complete`.

### 4.3. Event Types

The `event_data` object within the `events` list provides insight into the agent's internal state. The `event_type` key indicates the nature of the event.

| Event Type       | Description                                                 |
| ---------------- | ----------------------------------------------------------- |
| `plan_generated` | A strategic plan has been created or revised.               |
| `phase_start`    | The agent is beginning a new phase of its plan.             |
| `tool_result`    | A tool was executed.                                        |
| `token_update`   | Tokens were consumed in a call to the LLM.                  |
| `workaround`     | The agent performed a self-correction or optimization.      |
| `error`          | A general or unrecoverable error occurred during execution. |

### 4.4. The Result Object

When a task is `complete`, the `result` field will be populated with the final structured data from the agent, conforming to either the `CanonicalResponse` or `PromptReportResponse` schema.

* **`CanonicalResponse`**: For standard, ad-hoc queries.
    ```json
    {
      "direct_answer": "string",
      "key_metric": { "value": "string", "label": "string" } | null,
      "key_observations": [ { "text": "string" } ],
      "synthesis": [ { "text": "string" } ]
    }
    ```
* **`PromptReportResponse`**: For queries initiated via a pre-defined prompt.
    ```json
    {
      "title": "string",
      "executive_summary": "string",
      "report_sections": [
        { "title": "string", "content": "string (Markdown)" }
      ]
    }
    ```

## 5. Prerequisites

**IMPORTANT**: Before using the REST API, you must first configure the application through its web interface.

1.  Start the application server.
2.  Open a web browser and navigate to the application's URL (e.g., `http://127.0.0.1:5000`).
3.  Click on the **Config** tab.
4.  Enter and validate your LLM provider credentials and MCP server details.
5.  Once the UI shows a "Successfully configured" message, the REST API is ready to accept requests.

## 6. Full Workflow Example (cURL)

**1. Create a Session**

```bash
SESSION_ID=$(curl -s -X POST [http://127.0.0.1:5000/api/v1/sessions](http://127.0.0.1:5000/api/v1/sessions) | jq -r .session_id)
echo "Created Session: $SESSION_ID"
```

**2. Submit a Query**

```bash
TASK_URL=$(curl -s -X POST "[http://127.0.0.1:5000/api/v1/sessions/$SESSION_ID/query](http://127.0.0.1:5000/api/v1/sessions/$SESSION_ID/query)" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What is the business description for the DEMO_DB database?"}' | jq -r .status_url)
echo "Task URL: $TASK_URL"
```

**3. Poll for the Result with Intermediate Events**

**Note:** Save the script below as `check_status.sh`. It is designed to be a reusable utility.

```bash
#!/bin/bash
# check_status.sh
#
# This script polls a task status URL until the task is complete,
# printing new events as they arrive.

# --- 1. Argument Validation ---
# Check if a task URL path was provided as an argument.
if [ -z "$1" ]; then
  echo "Usage: ./check_status.sh <task_url_path>"
  echo "Example: ./check_status.sh /api/v1/tasks/some-task-id"
  exit 1
fi

# --- 2. Initialization ---
TASK_URL_PATH=$1
BASE_URL="[http://127.0.0.1:5000](http://127.0.0.1:5000)"
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
```

**4. Make the Script Executable and Run It**

```bash
# Make the script executable
chmod +x check_status.sh

# Run the script, passing the TASK_URL from Step 2 as the argument
./check_status.sh "$TASK_URL"
```

## 7. Troubleshooting

### "Created Session: null"

* **Symptom**: When running the "Create a Session" cURL command, the output is `Created Session: null`.
* **Cause**: This occurs because the application has not yet been configured with valid LLM and MCP credentials. The API returns an error message, and the `jq` command cannot find a `session_id` field in the error, so it outputs `null`.
* **Solution**: Follow the steps in the **Prerequisites** section to configure the application through the web UI. Once the configuration is successful, the command will work as expected.

</pre>
</body>
</html>