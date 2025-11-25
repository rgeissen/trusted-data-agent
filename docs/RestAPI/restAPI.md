# Trusted Data Agent REST API Documentation

## Table of Contents

1. [Introduction](#1-introduction)
2. [Authentication](#2-authentication)
   - [Access Tokens (Recommended)](#21-access-tokens-recommended)
   - [JWT Tokens](#22-jwt-tokens)
   - [Quick Start Guide](#23-quick-start-guide)
3. [API Endpoints](#3-api-endpoints)
   - [Authentication Endpoints](#31-authentication-endpoints)
   - [Access Token Management](#32-access-token-management)
   - [Application Configuration](#33-application-configuration)
   - [Session Management](#34-session-management)
   - [Query Execution](#35-query-execution)
   - [Task Management](#36-task-management)
   - [RAG Collection Management](#37-rag-collection-management)
   - [RAG Template System](#38-rag-template-system)
   - [MCP Server Management](#39-mcp-server-management)
   - [Session Analytics](#310-session-analytics)
4. [Data Models](#4-data-models)
5. [Code Examples](#5-code-examples)
6. [Security Best Practices](#6-security-best-practices)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Introduction

Welcome to the Trusted Data Agent (TDA) REST API. This API provides a programmatic interface to interact with the agent's powerful data analysis and querying capabilities.

The API is designed around an **asynchronous task-based architecture**. This pattern is ideal for handling potentially long-running agent processes in a robust and scalable way. Instead of holding a connection open while the agent works, you initiate a task and then poll a status endpoint to get progress updates and the final result. You can also cancel a running task if needed.

### Key Features

- **🔐 Secure Authentication**: Dual authentication system with JWT and long-lived access tokens
- **⚡ Asynchronous Query Execution**: Submit queries and poll for results without holding connections
- **🧠 RAG Collection Management**: Create and manage collections of query patterns for context-aware responses
- **📝 Template-Based Population**: Use modular templates to automatically generate RAG case studies
- **🤖 LLM-Assisted Generation**: Generate question/SQL pairs automatically from database schemas
- **🔌 MCP Server Integration**: Connect to multiple Model Context Protocol servers for data access
- **💬 Session Management**: Maintain conversation context across multiple queries
- **📊 Analytics & Monitoring**: Track token usage, costs, and performance metrics

### Base URL

All API endpoints are relative to your TDA instance:
```
http://your-tda-host:5000/api
```

For local development:
```
http://localhost:5000/api
http://127.0.0.1:5000/api
```

---

## 2. Authentication

The Trusted Data Agent REST API requires authentication for all endpoints except public registration. We support two authentication methods optimized for different use cases.

### 2.1. Access Tokens (Recommended)

**Best for:** REST API clients, automation scripts, CI/CD pipelines, external integrations

Access tokens are **long-lived API keys** that provide secure programmatic access without exposing credentials.

#### Features

✅ **Long-lived** - Configurable expiration (30/60/90/180/365 days) or never expires  
✅ **Secure** - SHA256 hashed storage, shown only once on creation  
✅ **Trackable** - Monitor usage count and last used timestamp  
✅ **Revocable** - Instantly revoke compromised tokens  
✅ **Multiple tokens** - Create separate tokens per application/environment  
✅ **Named** - Descriptive names for easy management (e.g., "Production Server")

#### Token Format

```
tda_<32-random-characters>
```

Example: `tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p`

#### Using Access Tokens

Include the token in the `Authorization` header with the `Bearer` scheme:

```bash
curl -X GET http://localhost:5000/api/v1/sessions \
  -H "Authorization: Bearer tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"
```

### 2.2. JWT Tokens

**Best for:** Web UI sessions, interactive applications, short-term access

JWT (JSON Web Tokens) are short-lived session tokens automatically managed by the web interface.

#### Features

✅ **Auto-expiration** - 24-hour lifetime  
✅ **Stateless** - No server-side session storage  
✅ **Automatic** - Managed by web UI  

#### Using JWT Tokens

```bash
# Login to get JWT token
JWT=$(curl -s -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}' \
  | jq -r '.token')

# Use JWT token in API calls
curl -X GET http://localhost:5000/api/v1/sessions \
  -H "Authorization: Bearer $JWT"
```

### 2.3. Quick Start Guide

#### Step 1: Register an Account

```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_user",
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "api_user",
    "email": "user@example.com"
  }
}
```

#### Step 2: Login to Get JWT Token

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_user",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "api_user",
    "email": "user@example.com",
    "user_uuid": "api_user_550e8400"
  }
}
```

#### Step 3: Create an Access Token

```bash
JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:5000/api/v1/auth/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Server",
    "expires_in_days": 90
  }'
```

**Response:**
```json
{
  "status": "success",
  "token": "tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p",
  "token_id": "abc123-def456-ghi789",
  "name": "Production Server",
  "created_at": "2025-11-25T10:00:00Z",
  "expires_at": "2026-02-25T10:00:00Z"
}
```

⚠️ **CRITICAL:** Copy the `token` value immediately! It cannot be retrieved later.

#### Step 4: Use Your Access Token

```bash
TOKEN="tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"

curl -X POST http://localhost:5000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN"
```

---

## 3. API Endpoints

The base URL for all endpoints is `/api`.

### 3.1. Authentication Endpoints

#### 3.1.1. Register User

Create a new user account.

**Endpoint:** `POST /auth/register`  
**Authentication:** None (public endpoint)

**Request Body:**
```json
{
  "username": "api_user",
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Validation Rules:**
- `username`: 3-50 characters, alphanumeric and underscores only
- `email`: Valid email format
- `password`: Minimum 8 characters

**Success Response:**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "api_user",
    "email": "user@example.com"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Validation failed or username/email already exists
- `429 Too Many Requests` - Rate limit exceeded (3 registrations per hour per IP)

#### 3.1.2. Login

Authenticate and receive a JWT token.

**Endpoint:** `POST /auth/login`  
**Authentication:** None (uses credentials)

**Request Body:**
```json
{
  "username": "api_user",
  "password": "SecurePassword123!"
}
```

**Success Response:**
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "api_user",
    "email": "user@example.com",
    "user_uuid": "api_user_550e8400"
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid username or password
- `429 Too Many Requests` - Rate limit exceeded (5 attempts per minute per IP)

**Token Lifetime:** 24 hours

#### 3.1.3. Logout

Invalidate the current JWT token (web UI only - access tokens should be revoked via API).

**Endpoint:** `POST /auth/logout`  
**Authentication:** Required (JWT token)

**Success Response:**
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

### 3.2. Access Token Management

#### 3.2.1. Create Access Token

Generate a new long-lived access token for API authentication.

**Endpoint:** `POST /api/v1/auth/tokens`  
**Authentication:** Required (JWT or access token)

**Request Body:**
```json
{
  "name": "Production Server",
  "expires_in_days": 90
}
```

**Parameters:**
- `name` (string, required): Descriptive name for the token (3-100 characters)
- `expires_in_days` (integer, optional): Expiration in days (30/60/90/180/365) or `null` for never

**Success Response:**
```json
{
  "status": "success",
  "token": "tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p",
  "token_id": "abc123-def456-ghi789",
  "name": "Production Server",
  "created_at": "2025-11-25T10:00:00Z",
  "expires_at": "2026-02-25T10:00:00Z"
}
```

⚠️ **Security Note:** The full token is shown **only once**. Store it securely immediately.

**Error Responses:**
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Authentication required

#### 3.2.2. List Access Tokens

Retrieve all access tokens for the authenticated user.

**Endpoint:** `GET /api/v1/auth/tokens`  
**Authentication:** Required (JWT or access token)

**Query Parameters:**
- `include_revoked` (boolean, optional): Include revoked tokens in response (default: `false`)

**Success Response:**
```json
{
  "status": "success",
  "tokens": [
    {
      "id": "abc123-def456-ghi789",
      "name": "Production Server",
      "token_prefix": "tda_1a2b3c...",
      "created_at": "2025-11-25T10:00:00Z",
      "last_used_at": "2025-11-25T14:30:00Z",
      "expires_at": "2026-02-25T10:00:00Z",
      "revoked": false,
      "revoked_at": null,
      "use_count": 142
    },
    {
      "id": "xyz789-uvw456-rst123",
      "name": "Development",
      "token_prefix": "tda_9z8y7x...",
      "created_at": "2025-11-20T09:00:00Z",
      "last_used_at": null,
      "expires_at": null,
      "revoked": true,
      "revoked_at": "2025-11-24T16:00:00Z",
      "use_count": 23
    }
  ]
}
```

**Token Fields:**
- `token_prefix`: First 10 characters for identification
- `last_used_at`: `null` if never used
- `expires_at`: `null` if no expiration
- `revoked`: Boolean indicating if token has been revoked
- `revoked_at`: Timestamp when token was revoked, `null` if active
- `use_count`: Total number of API calls with this token

**Note:** By default, only active tokens are returned. Set `include_revoked=true` to see revoked tokens in the audit trail.

#### 3.2.3. Revoke Access Token

Immediately revoke an access token, preventing further use. The token is marked as revoked and preserved in the audit trail.

**Endpoint:** `DELETE /api/v1/auth/tokens/{token_id}`  
**Authentication:** Required (JWT or access token)

**URL Parameters:**
- `token_id` (string, required): The token ID to revoke

**Success Response:**
```json
{
  "status": "success",
  "message": "Token revoked successfully"
}
```

**Error Responses:**
- `404 Not Found` - Token not found or doesn't belong to user
- `401 Unauthorized` - Authentication required

⚠️ **Note:** Revoked tokens are kept in the database for audit purposes but cannot be used for authentication. They remain visible in the token list with a "Revoked" status and timestamp. Revoked tokens cannot be reactivated. Create a new token if needed.

### 3.3. Application Configuration

**Note:** Exemplary configuration files for all supported providers can be found in the `docs/RestAPI/scripts/sample_configs` directory.

Initializes and validates the agent's core services, including the LLM provider and the MCP server connection. This is the first step required before creating sessions or submitting queries.

**Endpoint:** `POST /api/v1/configure`  
**Authentication:** Not required (global configuration)

**Request Body:**
    A JSON object containing the full configuration. The structure varies slightly by provider.

**Google, Anthropic, OpenAI:**
```json
{
  "provider": "Google",
  "model": "gemini-1.5-flash-latest",
  "credentials": {
    "apiKey": "YOUR_API_KEY"
  },
  "mcp_server": {
    "name": "my_mcp_server",
    "host": "localhost",
    "port": 8001,
    "path": "/mcp"
  }
}
```

**Friendli:**
```json
{
  "provider": "Friendli",
  "model": "google/gemma-3-27b-it",
  "credentials": {
    "apiKey": "YOUR_FRIENDLI_API_KEY",
    "friendli_endpoint_url": "YOUR_FRIENDLI_ENDPOINT_URL" 
  },
  "mcp_server": { ... }
}
```

**Amazon Bedrock:**
```json
{
  "provider": "Amazon",
  "model": "amazon.titan-text-express-v1",
  "credentials": {
    "aws_access_key_id": "YOUR_AWS_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_AWS_SECRET_KEY",
    "aws_region": "us-east-1"
  },
  "mcp_server": { ... }
}
```

**Ollama:**
```json
{
  "provider": "Ollama",
  "model": "llama2",
  "credentials": {
    "ollama_host": "http://localhost:11434"
  },
  "mcp_server": { ... }
}
```

**Success Response:**
```json
{
  "status": "success",
  "message": "MCP Server 'my_mcp_server' and LLM configured successfully."
}
```

**Error Responses:**
- `400 Bad Request` - Invalid configuration or authentication failed

### 3.4. Session Management

#### 3.4.1. Create a New Session

Creates a new, isolated conversation session for the agent. A session stores context and history for subsequent queries.

**Endpoint:** `POST /api/v1/sessions`  
**Authentication:** Required (JWT or access token)

**Request Body:** None

**Success Response:**
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

**Error Responses:**
- `503 Service Unavailable` - Application not configured (run `/api/v1/configure` first)
- `401 Unauthorized` - Authentication required

#### 3.4.2. List Sessions

Get a filtered and sorted list of all user sessions.

**Endpoint:** `GET /api/v1/sessions`  
**Authentication:** Required (JWT or access token)

**Query Parameters:**
- `search` (string, optional): Search query to filter sessions
- `sort` (string, optional): Sort order - `recent`, `oldest`, `tokens`, `turns` (default: `recent`)
- `filter_status` (string, optional): Filter by status - `all`, `success`, `partial`, `failed` (default: `all`)
- `filter_model` (string, optional): Filter by model name (default: `all`)
- `limit` (integer, optional): Maximum results (default: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Success Response:**
```json
{
  "sessions": [
    {
      "id": "session-uuid",
      "name": "Data Analysis Session",
      "created_at": "2025-11-19T10:00:00Z",
      "last_updated": "2025-11-19T10:15:00Z",
      "provider": "Google",
      "model": "gemini-1.5-flash",
      "input_tokens": 5000,
      "output_tokens": 3000,
      "turn_count": 3,
      "status": "success"
    }
  ],
  "total": 42
}
```

#### 3.4.3. Get Session Details

Get complete details for a specific session including timeline and RAG associations.

**Endpoint:** `GET /api/v1/sessions/{session_id}/details`  
**Authentication:** Required (JWT or access token)

**URL Parameters:**
- `session_id` (string, required): The session UUID

**Success Response:** Complete session data including `workflow_history`, `execution_trace`, and `rag_cases`

**Error Responses:**
- `404 Not Found` - Session not found
- `401 Unauthorized` - Authentication required

### 3.5. Query Execution

#### 3.5.1. Submit a Query

Submits a natural language query to a specific session. This initiates a background task for the agent to process the query.

**Endpoint:** `POST /api/v1/sessions/{session_id}/query`  
**Authentication:** Required (JWT or access token)

**URL Parameters:**
- `session_id` (string, required): The session UUID

**Request Body:**
```json
{
  "prompt": "Your natural language query for the agent."
}
```

**Success Response:**
```json
{
  "task_id": "task-9876-5432-1098-7654",
  "status_url": "/api/v1/tasks/task-9876-5432-1098-7654"
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `400 Bad Request` - Missing or invalid prompt
- `401 Unauthorized` - Authentication required

### 3.6. Task Management

#### 3.6.1. Get Task Status and Result

Polls for the status of a background task. This endpoint provides real-time progress updates through an event log and delivers the final result when the task is complete.

**Endpoint:** `GET /api/v1/tasks/{task_id}`  
**Authentication:** Required (JWT or access token)

**URL Parameters:**
- `task_id` (string, required): The task ID from "Submit a Query"

**Success Response:** See section **4. Data Models - The Task Object** for detailed structure.

**Error Responses:**
- `404 Not Found` - Task not found
- `401 Unauthorized` - Authentication required

#### 3.6.2. Cancel Task Execution

Requests cancellation of an actively running background task.

**Endpoint:** `POST /api/v1/tasks/{task_id}/cancel`  
**Authentication:** Required (JWT or access token)

**URL Parameters:**
- `task_id` (string, required): The task ID to cancel

**Request Body:** None

**Success Response:**
```json
{
  "status": "success",
  "message": "Cancellation request sent."
}
```

**Informational Response (Task Already Done):**
```json
{
  "status": "info",
  "message": "Task already completed."
}
```

**Error Responses:**
- `404 Not Found` - Task not found or already completed
- `401 Unauthorized` - Authentication required

### 3.7. RAG Collection Management

#### 3.7.1. Get All RAG Collections

Get all configured RAG collections with their active status.

**Endpoint:** `GET /api/v1/rag/collections`  
**Authentication:** Not required

**Success Response:**
        ```json
        {
          "status": "success",
          "collections": [
            {
              "id": 1,
              "name": "Support Queries",
              "description": "Customer support query patterns",
              "mcp_server_id": "prod_server",
              "enabled": true,
              "is_active": true
            }
          ]
        }
        ```

#### 3.6.2. Create RAG Collection

Create a new RAG collection. All collections must be associated with an MCP server.

* **Endpoint**: `POST /v1/rag/collections`
* **Method**: `POST`
* **Body**:
    ```json
    {
      "name": "Support Queries",
      "description": "Customer support query patterns",
      "mcp_server_id": "prod_server"
    }
    ```
* **Success Response**:
    * **Code**: `201 Created`
    * **Content**:
        ```json
        {
          "status": "success",
          "message": "Collection created successfully",
          "collection_id": 1,
          "mcp_server_id": "prod_server"
        }
        ```
* **Error Response**:
    * **Code**: `400 Bad Request` (if `mcp_server_id` is missing)

#### 3.6.3. Update RAG Collection

Update a RAG collection's metadata (name, description, MCP server association).

* **Endpoint**: `PUT /v1/rag/collections/{collection_id}`
* **Method**: `PUT`
* **URL Parameters**:
    * `collection_id` (integer, required): The collection ID
* **Body**:
    ```json
    {
      "name": "Updated Name",
      "description": "Updated description",
      "mcp_server_id": "new_server"
    }
    ```
* **Success Response**:
    * **Code**: `200 OK`
* **Error Response**:
    * **Code**: `400 Bad Request` (if attempting to remove `mcp_server_id`)
    * **Code**: `404 Not Found` (if collection doesn't exist)

#### 3.6.4. Delete RAG Collection

Delete a RAG collection and its vector store.

* **Endpoint**: `DELETE /v1/rag/collections/{collection_id}`
* **Method**: `DELETE`
* **URL Parameters**:
    * `collection_id` (integer, required): The collection ID
* **Success Response**:
    * **Code**: `200 OK`
* **Error Response**:
    * **Code**: `404 Not Found`

#### 3.6.5. Toggle RAG Collection

Enable or disable a RAG collection.

* **Endpoint**: `POST /v1/rag/collections/{collection_id}/toggle`
* **Method**: `POST`
* **URL Parameters**:
    * `collection_id` (integer, required): The collection ID
* **Body**:
    ```json
    {
      "enabled": true
    }
    ```
* **Success Response**:
    * **Code**: `200 OK`
* **Error Response**:
    * **Code**: `400 Bad Request` (if enabling a collection without MCP server assignment)

#### 3.6.6. Refresh RAG Collection

Refresh the vector store for a specific collection (rebuilds from case files).

* **Endpoint**: `POST /v1/rag/collections/{collection_id}/refresh`
* **Method**: `POST`
* **URL Parameters**:
    * `collection_id` (integer, required): The collection ID
* **Success Response**:
    * **Code**: `202 Accepted`
    * **Content**:
        ```json
        {
          "status": "success",
          "message": "Collection refresh started"
        }
        ```

#### 3.6.7. Submit Case Feedback

Submit user feedback (upvote/downvote) for a RAG case.

* **Endpoint**: `POST /v1/rag/cases/{case_id}/feedback`
* **Method**: `POST`
* **URL Parameters**:
    * `case_id` (string, required): The case UUID
* **Body**:
    ```json
    {
      "feedback_score": 1
    }
    ```
    * `feedback_score`: `-1` (downvote), `0` (neutral), `1` (upvote)
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "status": "success",
          "message": "Feedback submitted successfully",
          "case_id": "f3a16261-82a9-5d30-a654-64af74f19fcd",
          "feedback_score": 1
        }
        ```
* **Error Response**:
    * **Code**: `400 Bad Request` (invalid feedback_score)
    * **Code**: `404 Not Found` (case not found)

### 3.8. RAG Template System

The RAG Template System enables automatic generation of RAG case studies through modular templates with LLM-assisted question generation.

#### 3.8.1. List Available Templates

Get all registered RAG templates.

* **Endpoint**: `GET /v1/rag/templates`
* **Method**: `GET`
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "status": "success",
          "templates": [
            {
              "template_id": "sql_query_v1",
              "display_name": "SQL Query Template - Business Context",
              "description": "Two-phase strategy: Execute SQL and generate report",
              "version": "1.0.0",
              "status": "active"
            },
            {
              "template_id": "sql_query_doc_context_v1",
              "display_name": "SQL Query Template - Document Context",
              "description": "Three-phase strategy with document retrieval",
              "version": "1.0.0",
              "status": "active"
            }
          ]
        }
        ```

#### 3.6A.2. Get Template Plugin Info

Get detailed configuration for a specific template including manifest and UI field definitions.

* **Endpoint**: `GET /v1/rag/templates/{template_id}/plugin-info`
* **Method**: `GET`
* **URL Parameters**:
    * `template_id` (string, required): The template identifier (e.g., `sql_query_v1`)
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "status": "success",
          "template_id": "sql_query_v1",
          "plugin_info": {
            "name": "sql-query-basic",
            "version": "1.0.0",
            "display_name": "SQL Query Template - Business Context",
            "description": "Two-phase strategy...",
            "population_modes": {
              "manual": {
                "enabled": true,
                "input_variables": {
                  "database_name": {
                    "required": true,
                    "type": "string",
                    "description": "Target database name"
                  }
                }
              },
              "auto_generate": {
                "enabled": true,
                "input_variables": {
                  "context_topic": {
                    "required": true,
                    "type": "string",
                    "description": "Business context for generation"
                  },
                  "num_examples": {
                    "required": true,
                    "type": "integer",
                    "default": 5,
                    "min": 1,
                    "max": 1000,
                    "description": "Number of question/SQL pairs to generate"
                  }
                }
              }
            }
          }
        }
        ```

#### 3.6A.3. Generate Questions (LLM-Assisted)

Generate question/SQL pairs using LLM based on schema context and business requirements.

* **Endpoint**: `POST /v1/rag/generate-questions`
* **Method**: `POST`
* **Body**:
    ```json
    {
      "template_id": "sql_query_v1",
      "execution_context": "CREATE TABLE customers (id INT, name VARCHAR(100), email VARCHAR(100), status VARCHAR(20));\nCREATE TABLE orders (id INT, customer_id INT, total DECIMAL(10,2), created_at TIMESTAMP);",
      "subject": "Customer analytics and order reporting",
      "count": 10,
      "database_name": "sales_db"
    }
    ```
    * `template_id`: Template to use for generation
    * `execution_context`: Database schema information (from HELP TABLE, DESCRIBE, etc.)
    * `subject`: Business context topic for question generation
    * `count`: Number of question/SQL pairs to generate (1-1000)
    * `database_name`: Target database name
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "status": "success",
          "questions": [
            {
              "user_query": "Show all active customers",
              "sql_statement": "SELECT * FROM sales_db.customers WHERE status = 'active';"
            },
            {
              "user_query": "Count total orders by customer",
              "sql_statement": "SELECT customer_id, COUNT(*) as order_count FROM sales_db.orders GROUP BY customer_id;"
            }
          ],
          "input_tokens": 1234,
          "output_tokens": 567
        }
        ```
* **Error Response**:
    * **Code**: `400 Bad Request` (invalid parameters)
    * **Code**: `500 Internal Server Error` (LLM generation failed)

#### 3.6A.4. Populate Collection from Template

Populate a RAG collection with generated or manual examples using a template.

* **Endpoint**: `POST /v1/rag/collections/{collection_id}/populate`
* **Method**: `POST`
* **URL Parameters**:
    * `collection_id` (integer, required): The collection ID
* **Body**:
    ```json
    {
      "template_type": "sql_query",
      "examples": [
        {
          "user_query": "Show all active customers",
          "sql_statement": "SELECT * FROM sales_db.customers WHERE status = 'active';"
        },
        {
          "user_query": "Count total orders",
          "sql_statement": "SELECT COUNT(*) FROM sales_db.orders;"
        }
      ],
      "database_name": "sales_db",
      "mcp_tool_name": "base_readQuery"
    }
    ```
    * `template_type`: Currently only `"sql_query"` supported
    * `examples`: Array of question/SQL pairs
    * `database_name`: Optional database context
    * `mcp_tool_name`: Optional MCP tool override (default: `base_readQuery`)
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "status": "success",
          "message": "Successfully populated 2 cases",
          "results": {
            "total_examples": 2,
            "successful": 2,
            "failed": 0,
            "case_ids": [
              "abc123-def456-ghi789",
              "xyz789-uvw456-rst123"
            ],
            "errors": []
          }
        }
        ```
* **Error Response**:
    * **Code**: `400 Bad Request` (validation errors)
        ```json
        {
          "status": "error",
          "message": "Validation failed for some examples",
          "validation_issues": [
            {
              "example_index": 0,
              "field": "sql_statement",
              "issue": "SQL statement is empty or invalid"
            }
          ]
        }
        ```
    * **Code**: `404 Not Found` (collection not found)
    * **Code**: `500 Internal Server Error` (population failed)

### 3.7. MCP Server Management

#### 3.7.1. Get All MCP Servers

Get all configured MCP servers and the active server ID.

* **Endpoint**: `GET /v1/mcp/servers`
* **Method**: `GET`
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "status": "success",
          "servers": [
            {
              "id": "prod_server",
              "name": "Production Server",
              "host": "localhost",
              "port": 8001,
              "path": "/mcp"
            }
          ],
          "active_server_id": "prod_server"
        }
        ```

#### 3.7.2. Create MCP Server

Create a new MCP server configuration.

* **Endpoint**: `POST /v1/mcp/servers`
* **Method**: `POST`
* **Body**:
    ```json
    {
      "id": "dev_server",
      "name": "Development Server",
      "host": "localhost",
      "port": 8002,
      "path": "/mcp"
    }
    ```
* **Success Response**:
    * **Code**: `201 Created`
* **Error Response**:
    * **Code**: `400 Bad Request` (missing required fields)

#### 3.7.3. Update MCP Server

Update an existing MCP server configuration.

* **Endpoint**: `PUT /v1/mcp/servers/{server_id}`
* **Method**: `PUT`
* **URL Parameters**:
    * `server_id` (string, required): The server ID
* **Body**:
    ```json
    {
      "name": "Updated Name",
      "host": "newhost",
      "port": 8003
    }
    ```
* **Success Response**:
    * **Code**: `200 OK`
* **Error Response**:
    * **Code**: `404 Not Found`

#### 3.7.4. Delete MCP Server

Delete an MCP server configuration. Fails if any RAG collections are assigned to it.

* **Endpoint**: `DELETE /v1/mcp/servers/{server_id}`
* **Method**: `DELETE`
* **URL Parameters**:
    * `server_id` (string, required): The server ID
* **Success Response**:
    * **Code**: `200 OK`
* **Error Response**:
    * **Code**: `400 Bad Request` (if collections are assigned to this server)

#### 3.7.5. Activate MCP Server

Set an MCP server as the active server for the application.

* **Endpoint**: `POST /v1/mcp/servers/{server_id}/activate`
* **Method**: `POST`
* **URL Parameters**:
    * `server_id` (string, required): The server ID
* **Success Response**:
    * **Code**: `200 OK`
* **Error Response**:
    * **Code**: `404 Not Found`

### 3.8. Session Analytics and Management

#### 3.8.1. Get Session Analytics

Get comprehensive analytics across all sessions for the execution dashboard.

* **Endpoint**: `GET /v1/sessions/analytics`
* **Method**: `GET`
* **Headers**:
    * `X-TDA-User-UUID` (string, required): The unique identifier for the user.
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "total_sessions": 42,
          "total_tokens": {
            "input": 125000,
            "output": 85000,
            "total": 210000
          },
          "success_rate": 87.5,
          "estimated_cost": 2.10,
          "model_distribution": {
            "gemini-1.5-flash": 60.0,
            "gpt-4": 40.0
          },
          "top_champions": [
            {
              "query": "What databases are available?",
              "tokens": 320,
              "case_id": "abc-123"
            }
          ],
          "velocity_data": [
            {"hour": "2025-11-19 10:00", "count": 5}
          ]
        }
        ```

#### 3.8.2. Get Sessions List

Get a filtered and sorted list of all sessions.

* **Endpoint**: `GET /v1/sessions`
* **Method**: `GET`
* **Headers**:
    * `X-TDA-User-UUID` (string, required): The unique identifier for the user.
* **Query Parameters**:
    * `search` (string, optional): Search query to filter sessions
    * `sort` (string, optional): Sort order - `recent`, `oldest`, `tokens`, `turns` (default: `recent`)
    * `filter_status` (string, optional): Filter by status - `all`, `success`, `partial`, `failed` (default: `all`)
    * `filter_model` (string, optional): Filter by model name (default: `all`)
    * `limit` (integer, optional): Maximum number of results (default: 100)
    * `offset` (integer, optional): Pagination offset (default: 0)
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**:
        ```json
        {
          "sessions": [
            {
              "id": "session-uuid",
              "name": "Data Analysis Session",
              "created_at": "2025-11-19T10:00:00Z",
              "last_updated": "2025-11-19T10:15:00Z",
              "provider": "Google",
              "model": "gemini-1.5-flash",
              "input_tokens": 5000,
              "output_tokens": 3000,
              "turn_count": 3,
              "status": "success"
            }
          ],
          "total": 42
        }
        ```

#### 3.8.3. Get Session Details

Get complete details for a specific session including timeline and RAG associations.

* **Endpoint**: `GET /v1/sessions/{session_id}/details`
* **Method**: `GET`
* **Headers**:
    * `X-TDA-User-UUID` (string, required): The unique identifier for the user.
* **URL Parameters**:
    * `session_id` (string, required): The session UUID
* **Success Response**:
    * **Code**: `200 OK`
    * **Content**: Complete session data including `workflow_history`, `execution_trace`, and `rag_cases`
* **Error Response**:
    * **Code**: `404 Not Found`

## 4. Data Models

### 4.1. The Task Object

The Task Object is the central data structure for monitoring a query. It is returned by the `GET /api/v1/tasks/{task_id}` endpoint.

**Structure:**
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

**Fields:**
- `task_id`: Unique task identifier
- `status`: Task state (`pending`, `processing`, `complete`, `error`, `cancelled`, `cancelling`)
- `last_updated`: UTC timestamp of last update
- `events`: Chronological execution log
- `intermediate_data`: Tool call results as they are generated
- `result`: Final output (null until complete)

**Event Types:**

| Event Type       | Description                                    |
|------------------|------------------------------------------------|
| `plan_generated` | Strategic plan created or revised              |
| `phase_start`    | New phase of execution beginning               |
| `tool_result`    | Tool execution completed                       |
| `token_update`   | LLM tokens consumed                            |
| `workaround`     | Self-correction or optimization performed      |
| `cancelled`      | Execution stopped (user request)               |
| `error`          | Error occurred during execution                |

**Result Object Schemas:**

*CanonicalResponse* (standard queries):
```json
{
  "direct_answer": "string",
  "key_metric": { "value": "string", "label": "string" } | null,
  "key_observations": [ { "text": "string" } ],
  "synthesis": [ { "text": "string" } ]
}
```

*PromptReportResponse* (pre-defined prompts):
```json
{
  "title": "string",
  "executive_summary": "string",
  "report_sections": [
    { "title": "string", "content": "string (Markdown)" }
  ]
}
```

### 4.2. Authentication Token Comparison

| Feature | Access Tokens | JWT Tokens |
|---------|---------------|------------|
| **Format** | `tda_xxxxx...` (42 chars) | `eyJhbGci...` (variable) |
| **Lifetime** | Configurable or never | 24 hours fixed |
| **Use Case** | REST API, automation | Web UI sessions |
| **Storage** | SHA256 hashed | Stateless (not stored) |
| **Revocation** | Manual (instant) | Automatic (24h expiry) |
| **Tracking** | Use count, last used | No tracking |
| **Multiple** | Yes (per app/env) | One per session |
| **Security** | Shown once only | Regenerate on login |
| **Best For** | CI/CD, scripts, integrations | Interactive web use |

## 5. Code Examples

### 5.1. Complete Python Client

```python
#!/usr/bin/env python3
"""
Comprehensive TDA Python Client with access token management.
"""
import requests
import time
import os
from typing import Optional, Dict, Any

class TDAClient:
    """Trusted Data Agent API Client"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.jwt_token: Optional[str] = None
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        token = self.access_token or self.jwt_token
        if not token:
            raise Exception("Not authenticated. Call login() or set_access_token() first.")
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user account"""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        response.raise_for_status()
        return response.json()
    
    def login(self, username: str, password: str) -> bool:
        """Login and store JWT token"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.jwt_token = data.get("token")
            return True
        return False
    
    def set_access_token(self, token: str):
        """Set long-lived access token for authentication"""
        self.access_token = token
    
    def create_access_token(self, name: str, expires_in_days: Optional[int] = 90) -> Dict[str, Any]:
        """Create a new access token"""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/tokens",
            headers=self._get_headers(),
            json={
                "name": name,
                "expires_in_days": expires_in_days
            }
        )
        response.raise_for_status()
        return response.json()
    
    def list_access_tokens(self) -> Dict[str, Any]:
        """List all access tokens"""
        response = requests.get(
            f"{self.base_url}/api/v1/auth/tokens",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def revoke_access_token(self, token_id: str) -> Dict[str, Any]:
        """Revoke an access token"""
        response = requests.delete(
            f"{self.base_url}/api/v1/auth/tokens/{token_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def configure(self, provider: str, model: str, credentials: Dict[str, str], 
                  mcp_server: Dict[str, Any]) -> Dict[str, Any]:
        """Configure LLM and MCP server"""
        response = requests.post(
            f"{self.base_url}/api/v1/configure",
            json={
                "provider": provider,
                "model": model,
                "credentials": credentials,
                "mcp_server": mcp_server
            }
        )
        response.raise_for_status()
        return response.json()
    
    def create_session(self) -> str:
        """Create a new session and return session ID"""
        response = requests.post(
            f"{self.base_url}/api/v1/sessions",
            headers=self._get_headers()
        )
        response.raise_for_status()
        data = response.json()
        self.session_id = data.get("session_id")
        return self.session_id
    
    def submit_query(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit a query and return task info"""
        sid = session_id or self.session_id
        if not sid:
            raise Exception("No session ID. Call create_session() first.")
        
        response = requests.post(
            f"{self.base_url}/api/v1/sessions/{sid}/query",
            headers=self._get_headers(),
            json={"prompt": prompt}
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current task status"""
        response = requests.get(
            f"{self.base_url}/api/v1/tasks/{task_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_task(self, task_id: str, poll_interval: int = 2, 
                     max_wait: int = 300) -> Dict[str, Any]:
        """Wait for task completion with polling"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task = self.get_task_status(task_id)
            status = task.get("status")
            
            if status in ["complete", "error", "cancelled"]:
                return task
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete within {max_wait} seconds")
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a running task"""
        response = requests.post(
            f"{self.base_url}/api/v1/tasks/{task_id}/cancel",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def execute_query(self, prompt: str, session_id: Optional[str] = None, 
                     wait: bool = True) -> Dict[str, Any]:
        """Execute a query and optionally wait for completion"""
        task_info = self.submit_query(prompt, session_id)
        task_id = task_info.get("task_id")
        
        if wait:
            return self.wait_for_task(task_id)
        return task_info

# Usage Example
if __name__ == "__main__":
    # Initialize client
    client = TDAClient()
    
    # Option 1: Use access token (recommended)
    client.set_access_token(os.getenv("TDA_ACCESS_TOKEN"))
    
    # Option 2: Login with credentials
    # client.login("username", "password")
    
    # Create session and execute query
    session_id = client.create_session()
    print(f"Created session: {session_id}")
    
    # Submit query and wait for result
    result = client.execute_query("Show me all available databases")
    
    if result["status"] == "complete":
        print("Query completed!")
        print(f"Result: {result['result']}")
    else:
        print(f"Query failed: {result['status']}")
```

### 5.2. Bash/Shell Scripts

**Complete Automation Script:**
```bash
#!/bin/bash
# automated_analysis.sh - Daily database analysis automation

set -euo pipefail

# Configuration
TDA_URL="${TDA_URL:-http://localhost:5000}"
TDA_TOKEN="${TDA_ACCESS_TOKEN}"
DATABASE="${DATABASE:-production}"

if [ -z "$TDA_TOKEN" ]; then
    echo "Error: TDA_ACCESS_TOKEN environment variable not set"
    exit 1
fi

# Helper function for API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    
    if [ -z "$data" ]; then
        curl -s -X "$method" "$TDA_URL$endpoint" \
            -H "Authorization: Bearer $TDA_TOKEN"
    else
        curl -s -X "$method" "$TDA_URL$endpoint" \
            -H "Authorization: Bearer $TDA_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

# Create session
echo "Creating session..."
SESSION_ID=$(api_call POST "/api/v1/sessions" | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# Submit query
echo "Submitting query..."
QUERY="Analyze the $DATABASE database and provide key metrics"
TASK_INFO=$(api_call POST "/api/v1/sessions/$SESSION_ID/query" \
    "{\"prompt\": \"$QUERY\"}")
TASK_ID=$(echo "$TASK_INFO" | jq -r '.task_id')
echo "Task ID: $TASK_ID"

# Poll for completion
echo "Waiting for results..."
while true; do
    TASK_STATUS=$(api_call GET "/api/v1/tasks/$TASK_ID")
    STATUS=$(echo "$TASK_STATUS" | jq -r '.status')
    
    echo "Status: $STATUS"
    
    if [ "$STATUS" = "complete" ]; then
        echo "✓ Query completed successfully"
        echo "$TASK_STATUS" | jq '.result'
        break
    elif [ "$STATUS" = "error" ]; then
        echo "✗ Query failed"
        echo "$TASK_STATUS" | jq '.result'
        exit 1
    elif [ "$STATUS" = "cancelled" ]; then
        echo "⚠ Query was cancelled"
        exit 1
    fi
    
    sleep 2
done
```

### 5.3. JavaScript/Node.js Client

```javascript
const axios = require('axios');

class TDAClient {
    constructor(baseURL = 'http://localhost:5000') {
        this.baseURL = baseURL;
        this.jwtToken = null;
        this.accessToken = null;
        this.sessionId = null;
    }
    
    getHeaders() {
        const token = this.accessToken || this.jwtToken;
        if (!token) {
            throw new Error('Not authenticated');
        }
        
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }
    
    async register(username, email, password) {
        const response = await axios.post(
            `${this.baseURL}/auth/register`,
            { username, email, password }
        );
        return response.data;
    }
    
    async login(username, password) {
        try {
            const response = await axios.post(
                `${this.baseURL}/auth/login`,
                { username, password }
            );
            
            if (response.data.status === 'success') {
                this.jwtToken = response.data.token;
                return true;
            }
            return false;
        } catch (error) {
            console.error('Login failed:', error.message);
            return false;
        }
    }
    
    setAccessToken(token) {
        this.accessToken = token;
    }
    
    async createAccessToken(name, expiresInDays = 90) {
        const response = await axios.post(
            `${this.baseURL}/api/v1/auth/tokens`,
            { name, expires_in_days: expiresInDays },
            { headers: this.getHeaders() }
        );
        return response.data;
    }
    
    async createSession() {
        const response = await axios.post(
            `${this.baseURL}/api/v1/sessions`,
            {},
            { headers: this.getHeaders() }
        );
        this.sessionId = response.data.session_id;
        return this.sessionId;
    }
    
    async submitQuery(prompt, sessionId = null) {
        const sid = sessionId || this.sessionId;
        if (!sid) {
            throw new Error('No session ID');
        }
        
        const response = await axios.post(
            `${this.baseURL}/api/v1/sessions/${sid}/query`,
            { prompt },
            { headers: this.getHeaders() }
        );
        return response.data;
    }
    
    async getTaskStatus(taskId) {
        const response = await axios.get(
            `${this.baseURL}/api/v1/tasks/${taskId}`,
            { headers: this.getHeaders() }
        );
        return response.data;
    }
    
    async waitForTask(taskId, pollInterval = 2000, maxWait = 300000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWait) {
            const task = await this.getTaskStatus(taskId);
            const status = task.status;
            
            if (['complete', 'error', 'cancelled'].includes(status)) {
                return task;
            }
            
            await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
        
        throw new Error(`Task ${taskId} timeout after ${maxWait}ms`);
    }
    
    async executeQuery(prompt, sessionId = null, wait = true) {
        const taskInfo = await this.submitQuery(prompt, sessionId);
        const taskId = taskInfo.task_id;
        
        if (wait) {
            return await this.waitForTask(taskId);
        }
        return taskInfo;
    }
}

// Usage
(async () => {
    const client = new TDAClient();
    
    // Use access token
    client.setAccessToken(process.env.TDA_ACCESS_TOKEN);
    
    // Create session and execute query
    const sessionId = await client.createSession();
    console.log(`Created session: ${sessionId}`);
    
    const result = await client.executeQuery('Show me all databases');
    
    if (result.status === 'complete') {
        console.log('Query completed!');
        console.log('Result:', result.result);
    }
})();
```

### 5.4. cURL Examples

**Create Access Token:**
```bash
# Login first
JWT=$(curl -s -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_user","password":"your_pass"}' \
  | jq -r '.token')

# Create token
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Production","expires_in_days":90}' \
  | jq -r '.token')

echo "Your access token: $TOKEN"
echo "Save this token securely!"
```

**Complete Query Workflow:**
```bash
TOKEN="tda_your_token_here"

# Create session
SESSION=$(curl -s -X POST http://localhost:5000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.session_id')

# Submit query
TASK=$(curl -s -X POST http://localhost:5000/api/v1/sessions/$SESSION/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Show all databases"}' \
  | jq -r '.task_id')

# Poll for result
while true; do
    STATUS=$(curl -s http://localhost:5000/api/v1/tasks/$TASK \
      -H "Authorization: Bearer $TOKEN" \
      | jq -r '.status')
    
    if [ "$STATUS" = "complete" ]; then
        curl -s http://localhost:5000/api/v1/tasks/$TASK \
          -H "Authorization: Bearer $TOKEN" | jq '.result'
        break
    fi
    
    sleep 2
done
```

## 6. Security Best Practices

### 6.1. Token Storage

#### ✅ Recommended Approaches

**Environment Variables:**
```bash
# ~/.bashrc or ~/.zshrc
export TDA_ACCESS_TOKEN="tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"
export TDA_BASE_URL="https://tda.company.com"
```

**.env Files (with .gitignore):**
```bash
# .env
TDA_ACCESS_TOKEN=tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p
TDA_BASE_URL=https://tda.company.com
```

```python
# Python with python-dotenv
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TDA_ACCESS_TOKEN')
```

**Secret Managers:**
```python
# AWS Secrets Manager
import boto3
secrets = boto3.client('secretsmanager')
token = secrets.get_secret_value(SecretId='tda/access_token')['SecretString']

# Azure Key Vault
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
client = SecretClient(vault_url="https://myvault.vault.azure.net", 
                     credential=DefaultAzureCredential())
token = client.get_secret("tda-access-token").value
```

#### ❌ Bad Practices

```python
# DON'T hardcode tokens
TOKEN = "tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"

# DON'T commit tokens to git
# DON'T store tokens in plain text files
# DON'T log tokens in application logs
# DON'T share tokens via email/chat
```

### 6.2. Network Security

**Use HTTPS in Production:**
```python
# ✅ Production
BASE_URL = "https://tda.company.com"

# ⚠️ Development only
BASE_URL = "http://localhost:5000"
```

**Certificate Verification:**
```python
import requests

# ✅ Verify certificates (default)
response = requests.get(url, verify=True)

# ⚠️ Only disable for local development
response = requests.get(url, verify=False)
```

### 6.3. Token Management

**Create Separate Tokens per Application:**
```bash
# Production server
TOKEN_PROD=$(create_token "Production Server" 90)

# Development server
TOKEN_DEV=$(create_token "Development Server" 30)

# CI/CD Pipeline
TOKEN_CI=$(create_token "CI/CD Pipeline" 365)
```

**Rotate Tokens Regularly:**
```bash
#!/bin/bash
# rotate_tokens.sh - Automate token rotation

OLD_TOKEN_ID="token-id-to-revoke"
NEW_TOKEN_NAME="Production Server ($(date +%Y-%m-%d))"

# Create new token
NEW_TOKEN=$(create_access_token "$NEW_TOKEN_NAME" 90)

# Update application configuration
update_app_config "$NEW_TOKEN"

# Verify new token works
test_api_with_token "$NEW_TOKEN"

# Revoke old token only after verification
revoke_token "$OLD_TOKEN_ID"
```

**Implement Token Expiration Handling:**
```python
import time

class TDAClient:
    def __init__(self):
        self.token = None
        self.token_expires_at = 0
    
    def is_token_valid(self):
        if not self.token:
            return False
        
        # For access tokens with known expiration
        if self.token_expires_at:
            return time.time() < self.token_expires_at
        
        return True
    
    def execute_with_retry(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expired - refresh/re-login
                self.refresh_authentication()
                return func(*args, **kwargs)
            raise
```

### 6.4. Rate Limiting

The API implements rate limiting to prevent abuse:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/register` | 3 requests | 1 hour per IP |
| `/auth/login` | 5 requests | 1 minute per IP |
| All other endpoints | Varies | Based on usage |

**Handle Rate Limits:**
```python
import time

def api_call_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 6.5. Audit Logging

**Monitor Token Usage:**
```python
def list_token_usage():
    tokens = client.list_access_tokens()
    
    for token in tokens['tokens']:
        print(f"Token: {token['name']}")
        print(f"  Created: {token['created_at']}")
        print(f"  Last Used: {token['last_used_at']}")
        print(f"  Use Count: {token['use_count']}")
        print(f"  Status: {'Active' if not token['revoked'] else 'Revoked'}")
        
        # Alert on suspicious usage
        if token['use_count'] > 10000:
            alert_security_team(f"High usage detected: {token['name']}")
```

### 6.6. Security Checklist

- [ ] All tokens stored securely (environment variables or secret managers)
- [ ] HTTPS enabled for all production connections
- [ ] Separate tokens created for each application/environment
- [ ] Token expiration set appropriately (90 days for production)
- [ ] Regular token rotation schedule implemented
- [ ] Monitoring and alerting for token usage
- [ ] Rate limit handling implemented
- [ ] No tokens committed to version control
- [ ] Certificate verification enabled
- [ ] Token revocation process documented

---

## 7. Troubleshooting

### 7.1. Authentication Errors

#### "Invalid or revoked access token"

**Cause:** Token doesn't exist, was revoked, or expired  
**Solution:**
```bash
# List your tokens to check status
curl -X GET http://localhost:5000/api/v1/auth/tokens \
  -H "Authorization: Bearer $JWT"

# Create new token if needed
curl -X POST http://localhost:5000/api/v1/auth/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Token","expires_in_days":90}'
```

#### "Authentication required"

**Cause:** Missing or malformed `Authorization` header  
**Solution:**
```bash
# ✅ Correct format
curl -H "Authorization: Bearer tda_xxxxx..."

# ❌ Common mistakes
curl -H "Authorization: tda_xxxxx..."        # Missing "Bearer "
curl -H "Authorization: Bearer tda_xxxxx ..."  # Extra space after token
curl -H "Authorization:Bearer tda_xxxxx..."  # Missing space after colon
```

#### "Token expired"

**Cause:** JWT token older than 24 hours  
**Solution:** Login again to get new JWT token

```python
# Implement auto-refresh
def ensure_authenticated(client):
    try:
        return client.some_api_call()
    except TokenExpiredError:
        client.login(username, password)
        return client.some_api_call()
```

### 7.2. Configuration Errors

#### "Application not configured"

**Cause:** LLM and MCP server not set up  
**Solution:** Configure via API or web UI first

```bash
curl -X POST http://localhost:5000/api/v1/configure \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "Google",
    "model": "gemini-1.5-flash",
    "credentials": {"apiKey": "YOUR_KEY"},
    "mcp_server": {
      "name": "my_server",
      "host": "localhost",
      "port": 8001,
      "path": "/mcp"
    }
  }'
```

#### "MCP server connection failed"

**Cause:** MCP server not running or incorrect configuration  
**Solution:**
1. Verify MCP server is running
2. Check host/port/path configuration
3. Test connection: `curl http://localhost:8001/mcp`

### 7.3. Query Execution Errors

#### Task Status: "error"

**Cause:** Query execution failed  
**Solution:** Check the task `result` field for error details

```python
task = client.get_task_status(task_id)
if task['status'] == 'error':
    print("Error details:", task['result'])
    print("Events log:", task['events'])
```

#### Task Never Completes

**Cause:** Long-running query or server issue  
**Solution:**
1. Check task events for progress: `GET /api/v1/tasks/{task_id}`
2. Increase timeout in polling logic
3. Cancel and retry: `POST /api/v1/tasks/{task_id}/cancel`

### 7.4. Network Errors

#### "Connection refused"

**Cause:** TDA server not running or wrong URL  
**Solution:**
```bash
# Check if server is running
curl http://localhost:5000/

# Verify correct port
ps aux | grep trusted_data_agent

# Check logs
tail -f logs/tda.log
```

#### SSL/Certificate Errors

**Cause:** Self-signed certificate or expired cert  
**Solution:**
```python
# Development: Disable verification (not for production!)
import requests
import urllib3
urllib3.disable_warnings()
response = requests.get(url, verify=False)

# Production: Install proper certificate
# or add CA certificate to trusted store
```

### 7.5. Rate Limiting

#### "429 Too Many Requests"

**Cause:** Exceeded rate limits  
**Solution:**
```python
import time

def handle_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return True
    return False

# Use in requests
while True:
    response = requests.get(url, headers=headers)
    if not handle_rate_limit(response):
        break
```

### 7.6. Common Issues

#### "Session not found"

**Cause:** Session ID is invalid or expired  
**Solution:** Create new session

```python
session_id = client.create_session()
```

#### "Task not found"

**Cause:** Task ID is invalid or task was purged  
**Solution:** Submit query again

```python
task_info = client.submit_query(prompt)
task_id = task_info['task_id']
```

#### "Invalid JSON"

**Cause:** Malformed request body  
**Solution:** Validate JSON before sending

```python
import json

# Validate JSON
try:
    json.loads(request_body)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

### 7.7. Debugging Tips

**Enable Verbose Logging:**
```python
import logging
import http.client as http_client

http_client.HTTPConnection.debuglevel = 1
logging.basicConfig(level=logging.DEBUG)
```

**Inspect Full Response:**
```python
response = requests.post(url, headers=headers, json=data)
print("Status:", response.status_code)
print("Headers:", response.headers)
print("Body:", response.text)
```

**Test Authentication:**
```bash
# Verify token is valid
TOKEN="tda_your_token"
curl -v http://localhost:5000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN"
```

### 7.8. Getting Help

If you continue to experience issues:

1. **Check the logs:** `logs/tda.log` on the server
2. **Verify configuration:** Web UI → Config tab
3. **Test basic connectivity:** `curl http://localhost:5000/`
4. **Check token status:** `GET /api/v1/auth/tokens`
5. **Review error events:** Check task `events` array for detailed execution logs

---

## 8. Quick Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get JWT |
| POST | `/auth/logout` | Logout (web UI) |
| POST | `/api/v1/auth/tokens` | Create access token |
| GET | `/api/v1/auth/tokens` | List access tokens |
| DELETE | `/api/v1/auth/tokens/{id}` | Revoke access token |

### Session & Query Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/configure` | Configure LLM & MCP |
| POST | `/api/v1/sessions` | Create new session |
| GET | `/api/v1/sessions` | List sessions |
| GET | `/api/v1/sessions/{id}/details` | Get session details |
| POST | `/api/v1/sessions/{id}/query` | Submit query |
| GET | `/api/v1/tasks/{id}` | Get task status |
| POST | `/api/v1/tasks/{id}/cancel` | Cancel task |

### RAG Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/rag/collections` | List collections |
| POST | `/api/v1/rag/collections` | Create collection |
| PUT | `/api/v1/rag/collections/{id}` | Update collection |
| DELETE | `/api/v1/rag/collections/{id}` | Delete collection |
| POST | `/api/v1/rag/collections/{id}/toggle` | Enable/disable |
| POST | `/api/v1/rag/collections/{id}/refresh` | Refresh vectors |
| POST | `/api/v1/rag/collections/{id}/populate` | Populate from template |
| GET | `/api/v1/rag/templates` | List templates |
| POST | `/api/v1/rag/generate-questions` | Generate Q&A pairs |

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 202 | Accepted | Task submitted |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | Not configured |

---

## 9. Additional Resources

- **RAG Templates:** `docs/RAG_Templates/README.md`
- **Authentication Migration:** `docs/AUTH_ONLY_MIGRATION.md`
- **Sample Configurations:** `docs/RestAPI/scripts/sample_configs/`
- **Example Scripts:** `docs/RestAPI/scripts/`
- **Main Documentation:** `README.md`

---

**Last Updated:** November 25, 2025  
**API Version:** v1  
**Document Version:** 2.0.0