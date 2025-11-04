import argparse
import requests
import sys
import os

def get_user_uuid(uuid_file_path: str) -> str:
    """
    Reads the user UUID from a file. Exits if the file is not found or empty.
    """
    if not os.path.exists(uuid_file_path) or os.stat(uuid_file_path).st_size == 0:
        print(f"Error: User UUID file not found or is empty: {uuid_file_path}")
        print("Please run rest_run_query.sh first to generate a UUID.")
        sys.exit(1)
    with open(uuid_file_path, 'r') as f:
        return f.read().strip()

def cancel_task(base_url: str, task_id: str, user_uuid: str):
    """
    Sends a POST request to the TDA REST API to cancel a specific task.

    Args:
        base_url: The base URL of the Trusted Data Agent server (e.g., http://127.0.0.1:5000).
        task_id: The ID of the task to cancel.
        user_uuid: The UUID of the user initiating the cancellation.
    """
    cancel_url = f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/cancel"
    print(f"Attempting to cancel task {task_id} for user {user_uuid} at: {cancel_url}")

    headers = {
        "X-TDA-User-UUID": user_uuid
    }

    try:
        response = requests.post(cancel_url, headers=headers, timeout=10) # Added a timeout

        # Check if the request was successful
        if response.status_code == 200:
            try:
                response_data = response.json()
                status = response_data.get("status", "unknown")
                message = response_data.get("message", "No message received.")
                print(f"Server response ({response.status_code}): Status: {status}, Message: {message}")
            except requests.exceptions.JSONDecodeError:
                print(f"Error: Received non-JSON response from server (Status Code: {response.status_code}).")
                print(f"Raw response: {response.text}")
        elif response.status_code == 404:
             try:
                 response_data = response.json()
                 print(f"Error ({response.status_code}): {response_data.get('message', 'Task not found.')}")
             except requests.exceptions.JSONDecodeError:
                 print(f"Error: Task not found (Status Code: {response.status_code}). Server response was not valid JSON.")
                 print(f"Raw response: {response.text}")
        else:
            # Handle other potential errors (e.g., 500 Internal Server Error)
            print(f"Error: Received status code {response.status_code} from server.")
            try:
                # Try to print JSON error message if available
                error_data = response.json()
                print(f"Server error details: {error_data}")
            except requests.exceptions.JSONDecodeError:
                # Fallback to raw text if not JSON
                print(f"Raw server response: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the server at {base_url}. Is it running?")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: The request to {cancel_url} timed out.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred during the request: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cancel a running Trusted Data Agent task via the REST API.")

    parser.add_argument("task_id",
                        help="The unique ID of the task to be cancelled.")
    parser.add_argument("--base-url",
                        default="http://127.0.0.1:5000",
                        help="The base URL of the Trusted Data Agent server (default: http://127.0.0.1:5000)")
    parser.add_argument("--uuid-file",
                        default=".tda_user_uuid",
                        help="Path to the file storing the user UUID (default: .tda_user_uuid)")

    args = parser.parse_args()

    user_uuid = get_user_uuid(args.uuid_file)
    cancel_task(args.base_url, args.task_id, user_uuid)
