
import httpx
import json
import uuid
import os
import time

# Generate a random user UUID
user_uuid = str(uuid.uuid4())
session_id = None
base_url = "http://localhost:5050"

def configure_server():
    print("Configuring server...")
    config_data = {
        "provider": "Ollama",
        "model": "llama2",
        "server_name": "default",
        "host": os.environ.get("MCP_HOST", "localhost"),
        "port": os.environ.get("MCP_PORT", 8080),
        "path": "/api/v1",
        "ollama_host": "http://localhost:11434"
    }
    
    url = f"{base_url}/configure"
    headers = {"X-TDA-User-UUID": user_uuid}
    
    try:
        response = httpx.post(url, json=config_data, headers=headers)
        if response.status_code == 200 and response.json().get("status") == "success":
            print("Configuration successful")
            return True
        else:
            print(f"Configuration might have failed, but continuing: {response.status_code} {response.text}")
            # Even if it fails (e.g. already configured), we can try to proceed.
            return True
    except httpx.RequestError as e:
        print(f"Error configuring server: {e}")
        return False

def create_session():
    global session_id
    print("Creating session...")
    url = f"{base_url}/session"
    headers = {"X-TDA-User-UUID": user_uuid}
    
    try:
        response = httpx.post(url, headers=headers, json={})
        if response.status_code == 200:
            session_id = response.json()["id"]
            print(f"Session created: {session_id}")
            return True
        else:
            print(f"Failed to create session: {response.text}")
            return False
    except httpx.RequestError as e:
        print(f"Error creating session: {e}")
        return False

def ask_question(message):
    if not session_id:
        if not create_session():
            return

    print(f"Asking question: {message}")
    url = f"{base_url}/ask_stream"
    headers = {
        "X-TDA-User-UUID": user_uuid,
        "Accept": "text/event-stream"
    }
    data = {
        "message": message,
        "session_id": session_id
    }
    
    try:
        with httpx.stream("POST", url, headers=headers, json=data, timeout=None) as response:
            print("Response from server:")
            for line in response.iter_lines():
                if line.strip():
                    print(line)
    except httpx.RequestError as e:
        print(f"Error asking question: {e}")

if __name__ == "__main__":
    # Give the server a moment to start up
    time.sleep(5)
    
    if configure_server():
        ask_question("what are my top 5 customers based on revenue generated?")
    else:
        print("Could not configure server. Aborting.")
