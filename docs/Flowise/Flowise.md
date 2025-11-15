# Trusted Data Agent (TDA) Flowise Integration

## 1. Overview
This document details the architecture and configuration of the Flowise workflows used to interface with the Trusted Data Agent (TDA) REST API. The integration is split into two distinct workflows to separate administrative configuration from user interaction.

1.  **TDA Configure:** A one-time or on-demand workflow to initialize the agent’s connection to LLM and MCP services.
2.  **TDA Conversation:** An interactive chat workflow that manages user sessions, submits asynchronous queries, and polls for results.

---
## 2. Agent Flows
The agent flows are provided as exemplary scripts that can be imported into the flowise environment:
1. **TDA Configure Agent:** [TDA - Configure Agents.json](./scripts/TDA%20-%20Configure%20Agents.json)
2. **TDA Conversation Agent:** [TDA - Conversation Agents.json](./scripts/TDA%20-%20Conversation%20Agents.json)

---

## 3. Workflow A: TDA Configure
**Purpose:** This workflow performs the mandatory initialization of the TDA server. It must be executed successfully before any queries can be processed.

### 3.1. Script Reference
The agent flow is defined in [TDA - Configure Agents.json](./scripts/TDA%20-%20Configure%20Agents.json).

### 3.2 Visual Architecture
*(Reference: Screenshot 2025-11-15 at 18.36.24.png)*
> **Note:** Insert the screenshot of the TDA Configure flow here.

### 3.3 Node Configuration

#### **Node 1: Start Node**
Defines the global configuration variables required for the TDA connection.

* **Variables:**
    * `baseUrl`: The root address of the TDA server (e.g., `http://192.168.0.100:5050`).
    * `provider`: The LLM provider (e.g., `Google`).
    * `model`: The specific model ID (e.g., `gemini-2.0-flash`).
    * `apiKey`: The API credential for the LLM provider.
    * `mcpServerName`: Identifier for the Model Context Protocol server (e.g., `teradata_mcp_server`).
    * `mcpServerHost`: Host address for the MCP server.
    * `mcpServerPort`: Port number for the MCP server (e.g., `8888`).
    * `mcpServerPath`: API path for the MCP server (e.g., `/mcp`).
    * `tts_credentials_json`: (Optional) JSON string for Text-to-Speech credentials.

#### **Node 2: HTTP Request (TDA Configure)**
Sends the configuration payload to the TDA API.

* **Method:** `POST`
* **Endpoint:** `{{baseUrl}}/api/v1/configure`
* **Headers:** `Content-Type: application/json`
* **Body Structure:**
    ```json
    {
      "provider": "{{provider}}",
      "model": "{{model}}",
      "credentials": {
        "apiKey": "{{apiKey}}"
      },
      "mcp_server": {
        "name": "{{mcpServerName}}",
        "host": "{{mcpServerHost}}",
        "port": {{mcpServerPort}},
        "path": "{{mcpServerPath}}"
      },
      "tts_credentials_json": "{{tts_credentials_json}}"
    }
    ```
    *Note: The `port` field is passed as a number (integer), not a string.*

---

## 4. Workflow B: TDA Conversation
**Purpose:** This is the primary user interface flow. It handles the asynchronous "Submit & Poll" pattern required by the TDA API, manages session state, and parses complex JSON responses.

### 4.1. Script Reference
The agent flow is defined in [TDA - Conversation Agents.json](./scripts/TDA%20-%20Conversation%20Agents.json).

### 4.2 Visual Architecture
*(Reference: Screenshot 2025-11-15 at 18.36.36.png)*
> **Note:** Insert the screenshot of the TDA Conversation flow here.

### 4.3 Node Configuration

#### **Node 1: Start Node**
Accepts runtime variables from the chat interface or calling application.

* **Variables:**
    * `baseUrl`: The TDA server address.
    * `userUuid`: A unique identifier for the user (required for API authentication).
    * `prompt`: The natural language query from the user.
    * `sessionId`: (Optional) An existing session ID to maintain context.

#### **Node 2: Custom Tool (TDA Request)**
Executes the asynchronous API interaction logic.

* **Logic:**
    1.  **Session Check:** Checks if `sessionId` is provided. If empty, calls `POST /v1/sessions` to generate a new one.
    2.  **Submit Query:** Sends the `prompt` to `POST /v1/sessions/{id}/query` and receives a `task_id`.
    3.  **Poll Loop:** Repeatedly checks `GET /v1/tasks/{task_id}` until the status is `complete`.
    4.  **Output:** Returns the raw JSON result object.

#### **Node 3: Custom JS (Response Extractor)**
Parses the raw output from the TDA Request node to isolate specific data payloads (specifically TTS data).

* **Input Variable:** `$apiResponse` (Output from Node 2).
* **Script:**
    ```javascript
    // Variable to hold the parsed object
    let responseObj;

    // Check if $apiResponse is a string that needs parsing
    if (typeof $apiResponse === 'string') {
      try {
        responseObj = JSON.parse($apiResponse);
      } catch (e) {
        return { error: "Failed to parse apiResponse string." };
      }
    } else {
      // If it's not a string, assume it's already an object
      responseObj = $apiResponse;
    }

    // Check for tts_payload in the object
    if (responseObj && responseObj.tts_payload) {
      // Get the nested tts_payload object
      const payload = responseObj.tts_payload;

      // Create the new, single target JSON
      const targetJson = {
        direct_answer: payload.direct_answer,
        key_observations: payload.key_observations,
        synthesis: payload.synthesis
      };
      
      // Return the new object
      return targetJson;

    } else {
      // Handle cases where tts_payload is truly missing
      return {
        error: "tts_payload not found in the parsed apiResponse object."
      };
    }
    ```

#### **Node 4: Formatter (Optional)**
(Description depends on specific configuration, but generally used to convert the JSON object from Node 3 into a human-readable Markdown string for the chat window).

---

## 5. Troubleshooting

| Error | Probable Cause | Solution |
| :--- | :--- | :--- |
| **500 Internal Server Error (Configure)** | Invalid JSON format (e.g., Port sent as string). | Ensure `mcpServerPort` is passed as an integer in the JSON body. Verify `mcpServerName` contains no spaces. |
| **405 Method Not Allowed** | Incorrect URL pathing. | Check if `baseUrl` includes the endpoint path (e.g., `/api/v1`). `baseUrl` should only contain `http://IP:PORT`. |
| **Session ID Not Found** | Expired or invalid Session UUID. | Clear the `sessionId` input to force the workflow to generate a new session. |
| **Task Timed Out** | Query complexity exceeds polling limit. | Increase the `maxPolls` variable in the TDA Request Custom Tool script. |